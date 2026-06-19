package api

type Option func(*Server)

func WithStore(store Store) Option {
	return func(server *Server) {
		if store != nil {
			server.store = store
		}
	}
}
