package runtime

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/vgeshiktor/invoices-platform/apps/api-go/internal/api"
)

func TestSubprocessReportRunnerReadsSummaryOutput(t *testing.T) {
	workspaceRoot := t.TempDir()
	workerRoot := filepath.Join(workspaceRoot, "fake-workers")
	writeFakeReportModule(t, workerRoot, false)

	runner := NewSubprocessReportRunner(ReportRunnerConfig{
		WorkspaceRoot:    workspaceRoot,
		WorkerPythonPath: workerRoot,
		FilesDir:         "artifacts",
	})

	result, err := runner.RunReport(context.Background(), api.ReportRunRequest{
		Report: api.Report{
			ID:       "report-1",
			TenantID: "tenant-alpha",
		},
		InputDir: "fixtures/invoices_01_2026",
		Formats:  []string{"json", "pdf"},
	})
	if err != nil {
		t.Fatalf("run report: %v", err)
	}
	if result.Status != "ready" {
		t.Fatalf("expected ready status, got %#v", result)
	}
	if len(result.Artifacts) != 2 {
		t.Fatalf("expected selected artifacts, got %#v", result.Artifacts)
	}
	if result.Totals == nil || result.Totals.GrossTotal != 117 || result.Totals.VATTotal != 17 || result.Totals.NetTotal != 100 {
		t.Fatalf("expected parsed totals, got %#v", result.Totals)
	}
}

func TestSubprocessReportRunnerFailsWhenSummaryMissing(t *testing.T) {
	workspaceRoot := t.TempDir()
	workerRoot := filepath.Join(workspaceRoot, "fake-workers")
	writeFakeReportModule(t, workerRoot, true)

	runner := NewSubprocessReportRunner(ReportRunnerConfig{
		WorkspaceRoot:    workspaceRoot,
		WorkerPythonPath: workerRoot,
		FilesDir:         "artifacts",
	})

	result, err := runner.RunReport(context.Background(), api.ReportRunRequest{
		Report: api.Report{
			ID:       "report-1",
			TenantID: "tenant-alpha",
		},
		InputDir: "fixtures/invoices_01_2026",
		Formats:  []string{"json"},
	})
	if err == nil {
		t.Fatal("expected missing summary failure")
	}
	if result.Status != "failed" || result.Error == "" {
		t.Fatalf("expected failed result, got %#v", result)
	}
}

func writeFakeReportModule(t *testing.T, root string, skipSummary bool) {
	t.Helper()

	moduleDir := filepath.Join(root, "invplatform", "cli")
	if err := os.MkdirAll(moduleDir, 0o755); err != nil {
		t.Fatalf("mkdir mod dir: %v", err)
	}

	for _, path := range []string{
		filepath.Join(root, "invplatform", "__init__.py"),
		filepath.Join(moduleDir, "__init__.py"),
	} {
		if err := os.WriteFile(path, []byte(""), 0o644); err != nil {
			t.Fatalf("write %s: %v", path, err)
		}
	}

	script := `
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--input-dir")
parser.add_argument("--json-output")
parser.add_argument("--csv-output")
parser.add_argument("--summary-csv-output")
parser.add_argument("--pdf-output")
args = parser.parse_args()

for path in [args.json_output, args.csv_output, args.pdf_output]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("artifact", encoding="utf-8")

if not ` + boolLiteral(skipSummary) + `:
    target = Path(args.summary_csv_output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("metric,value\ninvoice_total,117\ninvoice_vat,17\n", encoding="utf-8")
`
	if err := os.WriteFile(filepath.Join(moduleDir, "invoices_report.py"), []byte(script), 0o644); err != nil {
		t.Fatalf("write fake report mod: %v", err)
	}
}
