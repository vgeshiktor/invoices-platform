package runtime

import (
	"bytes"
	"context"
	"encoding/csv"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/vgeshiktor/invoices-platform/apps/api-go/internal/api"
)

type ReportRunnerConfig struct {
	WorkspaceRoot    string
	PythonBin        string
	WorkerPythonPath string
	FilesDir         string
}

type SubprocessReportRunner struct {
	cfg ReportRunnerConfig
}

func NewSubprocessReportRunner(cfg ReportRunnerConfig) *SubprocessReportRunner {
	if cfg.WorkspaceRoot == "" {
		cfg.WorkspaceRoot = "."
	}
	if cfg.PythonBin == "" {
		cfg.PythonBin = "python"
	}
	if cfg.WorkerPythonPath == "" {
		cfg.WorkerPythonPath = filepath.Join(cfg.WorkspaceRoot, "apps", "workers-py", "src")
	}
	if cfg.FilesDir == "" {
		cfg.FilesDir = filepath.Join(cfg.WorkspaceRoot, "storage")
	}
	return &SubprocessReportRunner{cfg: cfg}
}

func (r *SubprocessReportRunner) RunReport(ctx context.Context, req api.ReportRunRequest) (api.ReportRunResult, error) {
	outputDir := filepath.Join(resolvePath(r.cfg.WorkspaceRoot, r.cfg.FilesDir), "reports", req.Report.TenantID, req.Report.ID)
	inputDir := resolvePath(r.cfg.WorkspaceRoot, req.InputDir)
	outputs := reportOutputs{
		jsonPath:       firstNonEmpty(req.JSONOutput, filepath.Join(outputDir, "invoice_report.json")),
		csvPath:        firstNonEmpty(req.CSVOutput, filepath.Join(outputDir, "invoice_report.csv")),
		summaryCSVPath: firstNonEmpty(req.SummaryCSVOutput, filepath.Join(outputDir, "invoice_report.summary.csv")),
		pdfPath:        firstNonEmpty(req.PDFOutput, filepath.Join(outputDir, "invoice_report.pdf")),
	}

	args := []string{
		"-m", "invplatform.cli.invoices_report",
		"--input-dir", inputDir,
		"--json-output", outputs.jsonPath,
		"--csv-output", outputs.csvPath,
		"--summary-csv-output", outputs.summaryCSVPath,
		"--pdf-output", outputs.pdfPath,
	}

	cmd := exec.CommandContext(ctx, r.cfg.PythonBin, args...)
	cmd.Dir = r.cfg.WorkspaceRoot
	cmd.Env = append(os.Environ(), "PYTHONPATH="+joinPythonPath(r.cfg.WorkerPythonPath, os.Getenv("PYTHONPATH")))

	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	runErr := cmd.Run()
	result := api.ReportRunResult{
		Artifacts: selectArtifacts(req.Formats, outputs),
	}

	totals, totalsErr := parseSummaryTotals(outputs.summaryCSVPath)
	if totalsErr == nil {
		result.Totals = totals
	}

	if runErr != nil {
		result.Status = "failed"
		result.Error = summarizeCommandFailure(runErr, stdout.String(), stderr.String())
		return result, errors.New(result.Error)
	}
	if err := ensureRequestedArtifacts(req.Formats, outputs); err != nil {
		result.Status = "failed"
		result.Error = err.Error()
		return result, errors.New(result.Error)
	}
	if totalsErr != nil {
		result.Status = "failed"
		result.Error = fmt.Sprintf("parse report totals: %v", totalsErr)
		return result, errors.New(result.Error)
	}

	result.Status = "ready"
	return result, nil
}

type reportOutputs struct {
	jsonPath       string
	csvPath        string
	summaryCSVPath string
	pdfPath        string
}

func selectArtifacts(formats []string, outputs reportOutputs) []api.ReportArtifact {
	items := make([]api.ReportArtifact, 0, len(formats))
	for _, format := range formats {
		switch format {
		case "json":
			items = append(items, api.ReportArtifact{Format: format, Path: outputs.jsonPath})
		case "csv":
			items = append(items, api.ReportArtifact{Format: format, Path: outputs.csvPath})
		case "summary_csv":
			items = append(items, api.ReportArtifact{Format: format, Path: outputs.summaryCSVPath})
		case "pdf":
			items = append(items, api.ReportArtifact{Format: format, Path: outputs.pdfPath})
		}
	}
	return items
}

func ensureRequestedArtifacts(formats []string, outputs reportOutputs) error {
	for _, artifact := range selectArtifacts(formats, outputs) {
		if _, err := os.Stat(artifact.Path); err != nil {
			return fmt.Errorf("missing requested artifact %s: %w", artifact.Format, err)
		}
	}
	return nil
}

func parseSummaryTotals(path string) (*api.ReportTotals, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	rows, err := reader.ReadAll()
	if err != nil {
		return nil, err
	}

	var gross float64
	var vat float64
	for _, row := range rows[1:] {
		if len(row) < 2 {
			continue
		}
		switch strings.TrimSpace(row[0]) {
		case "invoice_total":
			gross, _ = strconv.ParseFloat(strings.TrimSpace(row[1]), 64)
		case "invoice_vat":
			vat, _ = strconv.ParseFloat(strings.TrimSpace(row[1]), 64)
		}
	}

	return &api.ReportTotals{
		NetTotal:   gross - vat,
		VATTotal:   vat,
		GrossTotal: gross,
	}, nil
}
