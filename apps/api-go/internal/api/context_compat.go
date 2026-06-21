package api

import "context"

func contextWithValue(parent context.Context, key, value any) context.Context {
	return context.WithValue(parent, key, value)
}
