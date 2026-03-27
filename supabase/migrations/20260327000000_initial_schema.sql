-- =============================================================================
-- OSSPool Database Schema
-- Initial migration: users, projects, rankings, money_pools, donations, payouts
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- USERS
-- =============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_id TEXT UNIQUE NOT NULL,
    github_username TEXT NOT NULL,
    avatar_url TEXT,
    email TEXT,
    stripe_connect_account_id TEXT,
    is_maintainer BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_users_stripe_account ON users(stripe_connect_account_id) WHERE stripe_connect_account_id IS NOT NULL;

-- =============================================================================
-- PROJECTS
-- =============================================================================
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_url TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    language TEXT,
    owner_github_id TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,

    stars INTEGER DEFAULT 0 CHECK (stars >= 0),
    forks INTEGER DEFAULT 0 CHECK (forks >= 0),
    watchers INTEGER DEFAULT 0 CHECK (watchers >= 0),
    open_issues INTEGER DEFAULT 0 CHECK (open_issues >= 0),
    commit_frequency DOUBLE PRECISION DEFAULT 0,
    dependents_count INTEGER DEFAULT 0 CHECK (dependents_count >= 0),
    download_count INTEGER DEFAULT 0 CHECK (download_count >= 0),
    issue_close_rate DOUBLE PRECISION DEFAULT 0,
    stars_growth_rate INTEGER DEFAULT 0 CHECK (stars_growth_rate >= 0),
    last_commit_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_projects_active ON projects(is_active, created_at DESC) WHERE is_active = TRUE;
CREATE INDEX idx_projects_language ON projects(language) WHERE language IS NOT NULL;
CREATE INDEX idx_projects_owner ON projects(owner_github_id);
CREATE INDEX idx_projects_stars ON projects(stars DESC);
CREATE INDEX idx_projects_name_search ON projects USING gin(to_tsvector('english', name));

-- =============================================================================
-- PROJECT_OWNERS (many-to-many: users <-> projects)
-- =============================================================================
CREATE TABLE project_owners (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'owner',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(project_id, user_id)
);

CREATE INDEX idx_project_owners_project ON project_owners(project_id);
CREATE INDEX idx_project_owners_user ON project_owners(user_id);

-- =============================================================================
-- RANKINGS
-- =============================================================================
CREATE TABLE rankings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_name TEXT NOT NULL,
    github_url TEXT NOT NULL,
    rank INTEGER NOT NULL CHECK (rank >= 1),
    total_score DOUBLE PRECISION NOT NULL,
    breakdown JSONB NOT NULL DEFAULT '{}',
    period TEXT NOT NULL CHECK (period IN ('daily', 'weekly', 'monthly', 'yearly', 'all_time')),
    computed_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_rankings_period_rank ON rankings(period, rank);
CREATE INDEX idx_rankings_project ON rankings(project_id);
CREATE INDEX idx_rankings_score ON rankings(period, total_score DESC);
CREATE INDEX idx_rankings_computed ON rankings(computed_at DESC);

-- =============================================================================
-- MONEY POOLS
-- =============================================================================
CREATE TABLE money_pools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    target_amount_cents INTEGER NOT NULL CHECK (target_amount_cents > 0),
    current_amount_cents INTEGER DEFAULT 0 CHECK (current_amount_cents >= 0),
    matched_pool_cents INTEGER DEFAULT 0 CHECK (matched_pool_cents >= 0),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'distributing', 'completed', 'cancelled')),
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    match_ratio DOUBLE PRECISION DEFAULT 1.0,
    donor_count INTEGER DEFAULT 0 CHECK (donor_count >= 0),
    project_count INTEGER DEFAULT 0 CHECK (project_count >= 0),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT valid_date_range CHECK (end_date > start_date)
);

CREATE INDEX idx_pools_status ON money_pools(status);
CREATE INDEX idx_pools_dates ON money_pools(start_date, end_date);

-- =============================================================================
-- DONATIONS
-- =============================================================================
CREATE TABLE donations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pool_id UUID NOT NULL REFERENCES money_pools(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    donor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    matched_amount_cents INTEGER DEFAULT 0 CHECK (matched_amount_cents >= 0),
    stripe_payment_intent_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_donations_pool_created ON donations(pool_id, created_at DESC);
CREATE INDEX idx_donations_project ON donations(project_id);
CREATE INDEX idx_donations_donor ON donations(donor_id);

-- =============================================================================
-- PAYOUTS
-- =============================================================================
CREATE TABLE payouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pool_id UUID NOT NULL REFERENCES money_pools(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    recipient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    matched_amount_cents INTEGER DEFAULT 0 CHECK (matched_amount_cents >= 0),
    total_payout_cents INTEGER NOT NULL CHECK (total_payout_cents >= 0),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    stripe_transfer_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_payouts_pool ON payouts(pool_id);
CREATE INDEX idx_payouts_recipient_created ON payouts(recipient_id, created_at DESC);
CREATE INDEX idx_payouts_status ON payouts(status);
CREATE INDEX idx_payouts_stripe ON payouts(stripe_transfer_id) WHERE stripe_transfer_id IS NOT NULL;

-- =============================================================================
-- ROW-LEVEL SECURITY POLICIES
-- =============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_owners ENABLE ROW LEVEL SECURITY;
ALTER TABLE rankings ENABLE ROW LEVEL SECURITY;
ALTER TABLE money_pools ENABLE ROW LEVEL SECURITY;
ALTER TABLE donations ENABLE ROW LEVEL SECURITY;
ALTER TABLE payouts ENABLE ROW LEVEL SECURITY;

-- Users
CREATE POLICY "Anyone can read users"
    ON users FOR SELECT
    USING (TRUE);

CREATE POLICY "Users can update own profile"
    ON users FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Service role can manage users"
    ON users FOR ALL
    USING (auth.role() = 'service_role');

-- Projects
CREATE POLICY "Anyone can read active projects"
    ON projects FOR SELECT
    USING (is_active = TRUE);

CREATE POLICY "Service role can manage projects"
    ON projects FOR ALL
    USING (auth.role() = 'service_role');

-- Project owners
CREATE POLICY "Owners can read their projects"
    ON project_owners FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Service role can manage project owners"
    ON project_owners FOR ALL
    USING (auth.role() = 'service_role');

-- Rankings
CREATE POLICY "Anyone can read rankings"
    ON rankings FOR SELECT
    USING (TRUE);

CREATE POLICY "Service role can manage rankings"
    ON rankings FOR ALL
    USING (auth.role() = 'service_role');

-- Money pools
CREATE POLICY "Anyone can read pools"
    ON money_pools FOR SELECT
    USING (TRUE);

CREATE POLICY "Service role can manage pools"
    ON money_pools FOR ALL
    USING (auth.role() = 'service_role');

-- Donations: enforce donor_id = auth.uid() on insert
CREATE POLICY "Anyone can read donations"
    ON donations FOR SELECT
    USING (TRUE);

CREATE POLICY "Authenticated users can donate"
    ON donations FOR INSERT
    WITH CHECK (auth.role() = 'authenticated' AND donor_id = auth.uid());

CREATE POLICY "Service role can manage donations"
    ON donations FOR ALL
    USING (auth.role() = 'service_role');

-- Payouts
CREATE POLICY "Recipients can read own payouts"
    ON payouts FOR SELECT
    USING (recipient_id = auth.uid());

CREATE POLICY "Service role can manage payouts"
    ON payouts FOR ALL
    USING (auth.role() = 'service_role');

-- =============================================================================
-- TRIGGERS: auto-update updated_at
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER pools_updated_at
    BEFORE UPDATE ON money_pools
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
