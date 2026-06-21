package api

import (
	"context"
	"errors"
	"sort"
	"sync"
)

var ErrNotFound = errors.New("not found")

type Store interface {
	CreateSession(ctx context.Context, session Session) error
	GetSession(ctx context.Context, id string) (Session, error)
	UpdateSession(ctx context.Context, session Session) error
	DeleteSession(ctx context.Context, id string) error

	ListProviderConfigs(ctx context.Context, tenantID string) ([]ProviderConfig, error)
	GetProviderConfig(ctx context.Context, tenantID, id string) (ProviderConfig, error)
	CreateProviderConfig(ctx context.Context, item ProviderConfig) error
	UpdateProviderConfig(ctx context.Context, item ProviderConfig) error

	ListCollectionJobs(ctx context.Context, tenantID string) ([]CollectionJob, error)
	GetCollectionJob(ctx context.Context, tenantID, id string) (CollectionJob, error)
	CreateCollectionJob(ctx context.Context, item CollectionJob) error
	UpdateCollectionJob(ctx context.Context, item CollectionJob) error

	ListReports(ctx context.Context, tenantID string) ([]Report, error)
	GetReport(ctx context.Context, tenantID, id string) (Report, error)
	CreateReport(ctx context.Context, item Report) error
	UpdateReport(ctx context.Context, item Report) error

	ListSchedules(ctx context.Context, tenantID string) ([]Schedule, error)
	GetSchedule(ctx context.Context, tenantID, id string) (Schedule, error)
	CreateSchedule(ctx context.Context, item Schedule) error
	UpdateSchedule(ctx context.Context, item Schedule) error

	ListAuditEvents(ctx context.Context, tenantID, entityType, entityID string) ([]AuditEvent, error)
	CreateAuditEvent(ctx context.Context, item AuditEvent) error
}

type MemoryStore struct {
	mu              sync.RWMutex
	sessions        map[string]Session
	providerConfigs map[string]ProviderConfig
	collectionJobs  map[string]CollectionJob
	reports         map[string]Report
	schedules       map[string]Schedule
	auditEvents     map[string]AuditEvent
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{
		sessions:        make(map[string]Session),
		providerConfigs: make(map[string]ProviderConfig),
		collectionJobs:  make(map[string]CollectionJob),
		reports:         make(map[string]Report),
		schedules:       make(map[string]Schedule),
		auditEvents:     make(map[string]AuditEvent),
	}
}

func (m *MemoryStore) CreateSession(_ context.Context, session Session) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.sessions[session.ID] = session
	return nil
}

func (m *MemoryStore) GetSession(_ context.Context, id string) (Session, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	session, ok := m.sessions[id]
	if !ok {
		return Session{}, ErrNotFound
	}
	return session, nil
}

func (m *MemoryStore) UpdateSession(_ context.Context, session Session) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.sessions[session.ID]; !ok {
		return ErrNotFound
	}
	m.sessions[session.ID] = session
	return nil
}

func (m *MemoryStore) DeleteSession(_ context.Context, id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.sessions, id)
	return nil
}

func (m *MemoryStore) ListProviderConfigs(_ context.Context, tenantID string) ([]ProviderConfig, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	items := make([]ProviderConfig, 0, len(m.providerConfigs))
	for _, item := range m.providerConfigs {
		if item.TenantID == tenantID {
			items = append(items, item)
		}
	}
	sort.Slice(items, func(i, j int) bool {
		return items[i].UpdatedAt > items[j].UpdatedAt
	})
	return items, nil
}

func (m *MemoryStore) GetProviderConfig(_ context.Context, tenantID, id string) (ProviderConfig, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	item, ok := m.providerConfigs[id]
	if !ok || item.TenantID != tenantID {
		return ProviderConfig{}, ErrNotFound
	}
	return item, nil
}

func (m *MemoryStore) CreateProviderConfig(_ context.Context, item ProviderConfig) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.providerConfigs[item.ID] = item
	return nil
}

func (m *MemoryStore) UpdateProviderConfig(_ context.Context, item ProviderConfig) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.providerConfigs[item.ID]; !ok {
		return ErrNotFound
	}
	m.providerConfigs[item.ID] = item
	return nil
}

func (m *MemoryStore) ListCollectionJobs(_ context.Context, tenantID string) ([]CollectionJob, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	items := make([]CollectionJob, 0, len(m.collectionJobs))
	for _, item := range m.collectionJobs {
		if item.TenantID == tenantID {
			items = append(items, item)
		}
	}
	sort.Slice(items, func(i, j int) bool {
		return items[i].UpdatedAt > items[j].UpdatedAt
	})
	return items, nil
}

func (m *MemoryStore) GetCollectionJob(_ context.Context, tenantID, id string) (CollectionJob, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	item, ok := m.collectionJobs[id]
	if !ok || item.TenantID != tenantID {
		return CollectionJob{}, ErrNotFound
	}
	return item, nil
}

func (m *MemoryStore) CreateCollectionJob(_ context.Context, item CollectionJob) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.collectionJobs[item.ID] = item
	return nil
}

func (m *MemoryStore) UpdateCollectionJob(_ context.Context, item CollectionJob) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.collectionJobs[item.ID]; !ok {
		return ErrNotFound
	}
	m.collectionJobs[item.ID] = item
	return nil
}

func (m *MemoryStore) ListReports(_ context.Context, tenantID string) ([]Report, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	items := make([]Report, 0, len(m.reports))
	for _, item := range m.reports {
		if item.TenantID == tenantID {
			items = append(items, item)
		}
	}
	sort.Slice(items, func(i, j int) bool {
		return items[i].UpdatedAt > items[j].UpdatedAt
	})
	return items, nil
}

func (m *MemoryStore) GetReport(_ context.Context, tenantID, id string) (Report, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	item, ok := m.reports[id]
	if !ok || item.TenantID != tenantID {
		return Report{}, ErrNotFound
	}
	return item, nil
}

func (m *MemoryStore) CreateReport(_ context.Context, item Report) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.reports[item.ID] = item
	return nil
}

func (m *MemoryStore) UpdateReport(_ context.Context, item Report) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.reports[item.ID]; !ok {
		return ErrNotFound
	}
	m.reports[item.ID] = item
	return nil
}

func (m *MemoryStore) ListSchedules(_ context.Context, tenantID string) ([]Schedule, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	items := make([]Schedule, 0, len(m.schedules))
	for _, item := range m.schedules {
		if item.TenantID == tenantID {
			items = append(items, item)
		}
	}
	sort.Slice(items, func(i, j int) bool {
		return items[i].UpdatedAt > items[j].UpdatedAt
	})
	return items, nil
}

func (m *MemoryStore) GetSchedule(_ context.Context, tenantID, id string) (Schedule, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	item, ok := m.schedules[id]
	if !ok || item.TenantID != tenantID {
		return Schedule{}, ErrNotFound
	}
	return item, nil
}

func (m *MemoryStore) CreateSchedule(_ context.Context, item Schedule) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.schedules[item.ID] = item
	return nil
}

func (m *MemoryStore) UpdateSchedule(_ context.Context, item Schedule) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.schedules[item.ID]; !ok {
		return ErrNotFound
	}
	m.schedules[item.ID] = item
	return nil
}

func (m *MemoryStore) ListAuditEvents(_ context.Context, tenantID, entityType, entityID string) ([]AuditEvent, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	items := make([]AuditEvent, 0, len(m.auditEvents))
	for _, item := range m.auditEvents {
		if item.TenantID != tenantID {
			continue
		}
		if entityType != "" && item.EntityType != entityType {
			continue
		}
		if entityID != "" && item.EntityID != entityID {
			continue
		}
		items = append(items, item)
	}
	sort.Slice(items, func(i, j int) bool {
		return items[i].CreatedAt > items[j].CreatedAt
	})
	return items, nil
}

func (m *MemoryStore) CreateAuditEvent(_ context.Context, item AuditEvent) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.auditEvents[item.ID] = item
	return nil
}
