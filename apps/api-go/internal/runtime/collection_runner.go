package runtime

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/vgeshiktor/invoices-platform/apps/api-go/internal/api"
)

type CollectionRunnerConfig struct {
	WorkspaceRoot       string
	PythonBin           string
	WorkerPythonPath    string
	FilesDir            string
	GraphClientID       string
	GraphAuthority      string
	GraphTokenCachePath string
	MonthlyGmailArgs    string
	MonthlyGraphArgs    string
}

type SubprocessCollectionRunner struct {
	cfg CollectionRunnerConfig
}

func NewSubprocessCollectionRunner(cfg CollectionRunnerConfig) *SubprocessCollectionRunner {
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
	return &SubprocessCollectionRunner{cfg: cfg}
}

func (r *SubprocessCollectionRunner) RunCollectionJob(ctx context.Context, req api.CollectionRunRequest) (api.CollectionRunResult, error) {
	baseDir := filepath.Join(resolvePath(r.cfg.WorkspaceRoot, r.cfg.FilesDir), "collections", req.Job.TenantID, req.Job.ID)
	graphClientID := firstNonEmpty(req.GraphClientID, r.cfg.GraphClientID)
	graphAuthority := firstNonEmpty(req.GraphAuthority, r.cfg.GraphAuthority, "consumers")
	graphTokenCache := firstNonEmpty(req.GraphTokenCache, r.cfg.GraphTokenCachePath)

	graphExtraArgs := strings.TrimSpace(r.cfg.MonthlyGraphArgs)
	if graphAuthority != "" && !strings.Contains(graphExtraArgs, "--authority") {
		graphExtraArgs = joinArgs(graphExtraArgs, "--authority", graphAuthority)
	}
	if graphTokenCache != "" && !strings.Contains(graphExtraArgs, "--token-cache-path") {
		graphExtraArgs = joinArgs(graphExtraArgs, "--token-cache-path", graphTokenCache)
	}
	if req.InteractiveAuth && !strings.Contains(graphExtraArgs, "--interactive-auth") {
		graphExtraArgs = joinArgs(graphExtraArgs, "--interactive-auth")
	}

	args := []string{
		"-m", "invplatform.cli.monthly_invoices",
		"--providers", strings.Join(req.Job.Providers, ","),
		"--month", fmt.Sprintf("%d", req.Job.Month),
		"--year", fmt.Sprintf("%d", req.Job.Year),
		"--base-dir", baseDir,
	}
	if strings.TrimSpace(r.cfg.MonthlyGmailArgs) != "" {
		args = append(args, "--gmail-extra-args", strings.TrimSpace(r.cfg.MonthlyGmailArgs))
	}
	if graphExtraArgs != "" {
		args = append(args, "--graph-extra-args", graphExtraArgs)
	}
	if graphClientID != "" {
		args = append(args, "--graph-client-id", graphClientID)
	}

	cmd := exec.CommandContext(ctx, r.cfg.PythonBin, args...)
	cmd.Dir = r.cfg.WorkspaceRoot
	cmd.Env = append(os.Environ(),
		"PYTHONPATH="+joinPythonPath(r.cfg.WorkerPythonPath, os.Getenv("PYTHONPATH")),
		"GRAPH_AUTHORITY="+graphAuthority,
	)

	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	runErr := cmd.Run()
	summaryPath, invoicesDir, summaryStatus, summaryErr := collectSummary(baseDir)
	result := api.CollectionRunResult{
		RunSummaryPath: summaryPath,
		InvoicesDir:    invoicesDir,
	}

	if summaryErr == nil {
		if summaryStatus == "success" {
			result.Status = "succeeded"
		} else {
			result.Status = "failed"
			result.Error = fmt.Sprintf("collection summary status=%s", summaryStatus)
		}
	}

	if runErr != nil {
		result.Status = "failed"
		result.Error = pickError(result.Error, summarizeCommandFailure(runErr, stdout.String(), stderr.String()))
		return result, errors.New(result.Error)
	}
	if summaryErr != nil {
		result.Status = "failed"
		result.Error = fmt.Sprintf("missing collection run summary: %v", summaryErr)
		return result, errors.New(result.Error)
	}
	if result.Status == "failed" {
		return result, errors.New(result.Error)
	}
	return result, nil
}

type collectionSummary struct {
	Status          string `json:"status"`
	ConsolidatedDir string `json:"consolidated_dir"`
}

func collectSummary(baseDir string) (summaryPath string, invoicesDir string, status string, err error) {
	matches, globErr := filepath.Glob(filepath.Join(baseDir, "invoices_*", "run_summary.json"))
	if globErr != nil {
		return "", "", "", globErr
	}
	if len(matches) == 0 {
		return "", "", "", os.ErrNotExist
	}
	summaryPath = matches[0]
	invoicesDir = filepath.Dir(summaryPath)
	payload, readErr := os.ReadFile(summaryPath)
	if readErr != nil {
		return summaryPath, invoicesDir, "", readErr
	}
	var summary collectionSummary
	if err := json.Unmarshal(payload, &summary); err != nil {
		return summaryPath, invoicesDir, "", err
	}
	if summary.ConsolidatedDir != "" {
		invoicesDir = summary.ConsolidatedDir
	}
	return summaryPath, invoicesDir, strings.TrimSpace(summary.Status), nil
}

func summarizeCommandFailure(runErr error, stdout, stderr string) string {
	text := strings.TrimSpace(strings.Join([]string{stderr, stdout}, "\n"))
	text = strings.TrimSpace(text)
	if text == "" {
		return runErr.Error()
	}
	if len(text) > 500 {
		text = text[:500]
	}
	return text
}

func pickError(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

func joinArgs(parts ...string) string {
	filtered := make([]string, 0, len(parts))
	for _, part := range parts {
		if strings.TrimSpace(part) != "" {
			filtered = append(filtered, strings.TrimSpace(part))
		}
	}
	return strings.Join(filtered, " ")
}

func joinPythonPath(extra, existing string) string {
	if existing == "" {
		return extra
	}
	return extra + string(os.PathListSeparator) + existing
}

func resolvePath(workspaceRoot, value string) string {
	if filepath.IsAbs(value) {
		return value
	}
	return filepath.Join(workspaceRoot, value)
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}
