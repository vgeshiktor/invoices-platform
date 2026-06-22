package api

import "context"

type ReportRunner interface {
	RunReport(ctx context.Context, req ReportRunRequest) (ReportRunResult, error)
}

type ReportRunRequest struct {
	Report           Report
	InputDir         string
	Formats          []string
	JSONOutput       string
	CSVOutput        string
	SummaryCSVOutput string
	PDFOutput        string
}

type ReportRunResult struct {
	Artifacts []ReportArtifact
	Totals    *ReportTotals
	Status    string
	Error     string
}

type noopReportRunner struct{}

func (noopReportRunner) RunReport(_ context.Context, req ReportRunRequest) (ReportRunResult, error) {
	return ReportRunResult{
		Artifacts: append([]ReportArtifact(nil), req.Report.Artifacts...),
		Totals:    req.Report.Totals,
		Status:    "ready",
	}, nil
}
