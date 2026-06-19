package main

import (
	"context"
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

	workspaceRoot, err := os.Getwd()
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

	server := api.NewServer(api.WithStore(store), api.WithCollectionRunner(runner))
	log.Printf("api-go listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, server.Handler()))
}
