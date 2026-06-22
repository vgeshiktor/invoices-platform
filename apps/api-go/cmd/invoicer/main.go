package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/vgeshiktor/invoices-platform/apps/api-go/internal/api"
	"github.com/vgeshiktor/invoices-platform/apps/api-go/internal/runtime"
	"github.com/vgeshiktor/invoices-platform/apps/api-go/internal/storage"
)

func main() {
	addr := ":8080"
	databaseURL := strings.TrimSpace(os.Getenv("DATABASE_URL"))
	if databaseURL == "" {
		log.Fatal("DATABASE_URL is required")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	store, err := storage.Open(ctx, databaseURL)
	if err != nil {
		log.Fatalf("open postgres store: %v", err)
	}
	defer store.Close()

	if err := store.Migrate(ctx); err != nil {
		log.Fatalf("migrate postgres store: %v", err)
	}

	workspaceRoot, err := findWorkspaceRoot()
	if err != nil {
		log.Fatalf("resolve workspace root: %v", err)
	}
	runner := runtime.NewSubprocessCollectionRunner(runtime.CollectionRunnerConfig{
		WorkspaceRoot:       workspaceRoot,
		WorkerPythonPath:    filepath.Join(workspaceRoot, "apps", "workers-py", "src"),
		FilesDir:            strings.TrimSpace(os.Getenv("FILES_DIR")),
		GraphClientID:       strings.TrimSpace(os.Getenv("GRAPH_CLIENT_ID")),
		GraphAuthority:      strings.TrimSpace(os.Getenv("GRAPH_AUTHORITY")),
		GraphTokenCachePath: strings.TrimSpace(os.Getenv("GRAPH_TOKEN_CACHE_PATH")),
		MonthlyGmailArgs:    strings.TrimSpace(os.Getenv("MONTHLY_GMAIL_ARGS")),
		MonthlyGraphArgs:    strings.TrimSpace(os.Getenv("MONTHLY_GRAPH_ARGS")),
	})
	reportRunner := runtime.NewSubprocessReportRunner(runtime.ReportRunnerConfig{
		WorkspaceRoot:    workspaceRoot,
		WorkerPythonPath: filepath.Join(workspaceRoot, "apps", "workers-py", "src"),
		FilesDir:         strings.TrimSpace(os.Getenv("FILES_DIR")),
	})

	server := api.NewServer(
		api.WithStore(store),
		api.WithCollectionRunner(runner),
		api.WithReportRunner(reportRunner),
	)
	log.Printf("api-go listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, server.Handler()))
}

func findWorkspaceRoot() (string, error) {
	if root := strings.TrimSpace(os.Getenv("WORKSPACE_ROOT")); root != "" {
		return root, nil
	}

	wd, err := os.Getwd()
	if err != nil {
		return "", err
	}

	for dir := wd; ; dir = filepath.Dir(dir) {
		if _, err := os.Stat(filepath.Join(dir, "apps", "workers-py", "src")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
	}

	return "", fmt.Errorf("could not locate repo root from %s", wd)
}
