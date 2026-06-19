package runtime

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/vgeshiktor/invoices-platform/apps/api-go/internal/api"
)

func TestSubprocessCollectionRunnerReadsRealSummaryOutput(t *testing.T) {
	workspaceRoot := t.TempDir()
	workerRoot := filepath.Join(workspaceRoot, "fake-workers")
	writeFakeMonthlyModule(t, workerRoot, false)

	runner := NewSubprocessCollectionRunner(CollectionRunnerConfig{
		WorkspaceRoot:    workspaceRoot,
		WorkerPythonPath: workerRoot,
		FilesDir:         "artifacts",
	})

	result, err := runner.RunCollectionJob(context.Background(), api.CollectionRunRequest{
		Job: api.CollectionJob{
			ID:        "job-1",
			TenantID:  "tenant-alpha",
			Providers: []string{"gmail"},
			Month:     6,
			Year:      2026,
		},
	})
	if err != nil {
		t.Fatalf("run collection job: %v", err)
	}
	if result.Status != "succeeded" {
		t.Fatalf("expected succeeded status, got %#v", result)
	}
	if result.RunSummaryPath == "" || result.InvoicesDir == "" {
		t.Fatalf("expected summary paths, got %#v", result)
	}
}

func TestSubprocessCollectionRunnerFailsWhenSummaryMissing(t *testing.T) {
	workspaceRoot := t.TempDir()
	workerRoot := filepath.Join(workspaceRoot, "fake-workers")
	writeFakeMonthlyModule(t, workerRoot, true)

	runner := NewSubprocessCollectionRunner(CollectionRunnerConfig{
		WorkspaceRoot:    workspaceRoot,
		WorkerPythonPath: workerRoot,
		FilesDir:         "artifacts",
	})

	result, err := runner.RunCollectionJob(context.Background(), api.CollectionRunRequest{
		Job: api.CollectionJob{
			ID:        "job-1",
			TenantID:  "tenant-alpha",
			Providers: []string{"gmail"},
			Month:     6,
			Year:      2026,
		},
	})
	if err == nil {
		t.Fatal("expected missing summary failure")
	}
	if result.Status != "failed" || result.Error == "" {
		t.Fatalf("expected failed result, got %#v", result)
	}
}

func writeFakeMonthlyModule(t *testing.T, root string, skipSummary bool) {
	t.Helper()

	moduleDir := filepath.Join(root, "invplatform", "cli")
	if err := os.MkdirAll(moduleDir, 0o755); err != nil {
		t.Fatalf("mkdir module dir: %v", err)
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
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--providers")
parser.add_argument("--month", type=int)
parser.add_argument("--year", type=int)
parser.add_argument("--base-dir")
parser.add_argument("--graph-extra-args", default="")
parser.add_argument("--gmail-extra-args", default="")
parser.add_argument("--graph-client-id", default="")
args = parser.parse_args()
label = f"{args.month:02d}_{args.year}"
dest = Path(args.base_dir) / f"invoices_{label}"
dest.mkdir(parents=True, exist_ok=True)
if not ` + boolLiteral(skipSummary) + `:
    (dest / "run_summary.json").write_text(json.dumps({
        "status": "success",
        "consolidated_dir": str(dest),
        "providers": {"gmail": {"returncode": 0}}
    }), encoding="utf-8")
`
	if err := os.WriteFile(filepath.Join(moduleDir, "monthly_invoices.py"), []byte(script), 0o644); err != nil {
		t.Fatalf("write fake monthly module: %v", err)
	}
}

func boolLiteral(value bool) string {
	if value {
		return "True"
	}
	return "False"
}
