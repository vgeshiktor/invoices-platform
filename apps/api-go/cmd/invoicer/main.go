package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/vgeshiktor/invoices-platform/apps/api-go/internal/api"
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

	server := api.NewServer(api.WithStore(store))
	log.Printf("api-go listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, server.Handler()))
}
