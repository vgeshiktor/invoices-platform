package api

import "context"

type CollectionRunner interface {
	RunCollectionJob(ctx context.Context, req CollectionRunRequest) (CollectionRunResult, error)
}

type CollectionRunRequest struct {
	Job             CollectionJob
	GraphClientID   string
	GraphAuthority  string
	GraphTokenCache string
	InteractiveAuth bool
	RequestID       string
}

type CollectionRunResult struct {
	RunSummaryPath string
	InvoicesDir    string
	Status         string
	Error          string
}

type noopCollectionRunner struct{}

func (noopCollectionRunner) RunCollectionJob(_ context.Context, req CollectionRunRequest) (CollectionRunResult, error) {
	return CollectionRunResult{
		RunSummaryPath: req.Job.RunSummaryPath,
		InvoicesDir:    req.Job.InvoicesDir,
		Status:         "succeeded",
	}, nil
}
