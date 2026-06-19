package api

type Option func(*Server)

func WithStore(store Store) Option {
	return func(server *Server) {
		if store != nil {
			server.store = store
		}
	}
}

func WithCollectionRunner(runner CollectionRunner) Option {
	return func(server *Server) {
		if runner != nil {
			server.collectionRunner = runner
		}
	}
}

func WithReportRunner(runner ReportRunner) Option {
	return func(server *Server) {
		if runner != nil {
			server.reportRunner = runner
		}
	}
}
