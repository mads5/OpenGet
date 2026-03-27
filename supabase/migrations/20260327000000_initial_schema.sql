-- =============================================================================
-- OpenGet Database Schema
-- Tables: users, repos, contributors, repo_contributors, pool, donations, payouts
-- =============================================================================

-- Drop old tables (from previous schema versions) and new tables to allow re-run
DROP TABLE IF EXISTS payouts CASCADE;
DROP TABLE IF EXISTS donations CASCADE;
DROP TABLE IF EXISTS pool CASCADE;
DROP TABLE IF EXISTS repo_contributors CASCADE;
DROP TABLE IF EXISTS contributors CASCADE;
DROP TABLE IF EXISTS repos CASCADE;
DROP TABLE IF EXISTS project_owners CASCADE;
DROP TABLE IF EXISTS rankings CASCADE;
DROP TABLE IF EXISTS money_pools CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop old functions/triggers that may conflict
DROP FUNCTION IF EXISTS handle_new_user() CASCADE;
DROP FUNCTION IF EXISTS update_updated_at() CASCADE;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- USERS (GitHub OAuth via Supabase Auth)
-- =============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_id TEXT UNIQUE NOT NULL,
    github_username TEXT NOT NULL,
    avatar_url TEXT,
    display_name TEXT,
    email TEXT,
    stripe_connect_account_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_users_github_username ON users(github_username);
CREATE INDEX idx_users_stripe ON users(stripe_connect_account_id) WHERE stripe_connect_account_id IS NOT NULL;

-- =============================================================================
-- REPOS (listed GitHub repositories, deduplicated by github_url)
-- =============================================================================
CREATE TABLE repos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_url TEXT UNIQUE NOT NULL,
    owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    description TEXT,
    language TEXT,
    stars INTEGER DEFAULT 0 CHECK (stars >= 0),
    forks INTEGER DEFAULT 0 CHECK (forks >= 0),
    listed_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    contributor_count INTEGER DEFAULT 0 CHECK (contributor_count >= 0),
    contributors_fetched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_repos_stars ON repos(stars DESC);
CREATE INDEX idx_repos_listed_by ON repos(listed_by);
CREATE INDEX idx_repos_full_name ON repos(full_name);
CREATE INDEX idx_repos_language ON repos(language) WHERE language IS NOT NULL;

-- =============================================================================
-- CONTRIBUTORS (unique GitHub users who contribute to listed repos)
-- =============================================================================
CREATE TABLE contributors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_username TEXT UNIQUE NOT NULL,
    github_id TEXT,
    avatar_url TEXT,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    total_score DOUBLE PRECISION DEFAULT 0 CHECK (total_score >= 0),
    repo_count INTEGER DEFAULT 0 CHECK (repo_count >= 0),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_contributors_score ON contributors(total_score DESC);
CREATE INDEX idx_contributors_user ON contributors(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_contributors_github ON contributors(github_username);

-- =============================================================================
-- REPO_CONTRIBUTORS (per-repo contribution metrics for each contributor)
-- =============================================================================
CREATE TABLE repo_contributors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_id UUID NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    contributor_id UUID NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    commits INTEGER DEFAULT 0 CHECK (commits >= 0),
    prs_merged INTEGER DEFAULT 0 CHECK (prs_merged >= 0),
    lines_added INTEGER DEFAULT 0 CHECK (lines_added >= 0),
    lines_removed INTEGER DEFAULT 0 CHECK (lines_removed >= 0),
    reviews INTEGER DEFAULT 0 CHECK (reviews >= 0),
    issues_closed INTEGER DEFAULT 0 CHECK (issues_closed >= 0),
    last_contribution_at TIMESTAMPTZ,
    score DOUBLE PRECISION DEFAULT 0 CHECK (score >= 0),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(repo_id, contributor_id)
);

CREATE INDEX idx_rc_repo ON repo_contributors(repo_id);
CREATE INDEX idx_rc_contributor ON repo_contributors(contributor_id);
CREATE INDEX idx_rc_score ON repo_contributors(score DESC);

-- =============================================================================
-- POOL (global funding pool -- typically one active at a time)
-- =============================================================================
CREATE TABLE pool (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    total_amount_cents INTEGER DEFAULT 0 CHECK (total_amount_cents >= 0),
    donor_count INTEGER DEFAULT 0 CHECK (donor_count >= 0),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'distributing', 'completed')),
    round_start TIMESTAMPTZ NOT NULL,
    round_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT valid_round_dates CHECK (round_end > round_start)
);

CREATE INDEX idx_pool_status ON pool(status);

-- =============================================================================
-- DONATIONS (individual contributions to the global pool)
-- =============================================================================
CREATE TABLE donations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pool_id UUID NOT NULL REFERENCES pool(id) ON DELETE CASCADE,
    donor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    currency TEXT DEFAULT 'usd',
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_donations_pool ON donations(pool_id, created_at DESC);
CREATE INDEX idx_donations_donor ON donations(donor_id);

-- =============================================================================
-- PAYOUTS (distributed to contributors from the pool)
-- =============================================================================
CREATE TABLE payouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pool_id UUID NOT NULL REFERENCES pool(id) ON DELETE CASCADE,
    contributor_id UUID NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    score_snapshot DOUBLE PRECISION DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    stripe_transfer_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_payouts_pool ON payouts(pool_id);
CREATE INDEX idx_payouts_contributor ON payouts(contributor_id, created_at DESC);
CREATE INDEX idx_payouts_status ON payouts(status);

-- =============================================================================
-- ROW-LEVEL SECURITY
-- =============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE repos ENABLE ROW LEVEL SECURITY;
ALTER TABLE contributors ENABLE ROW LEVEL SECURITY;
ALTER TABLE repo_contributors ENABLE ROW LEVEL SECURITY;
ALTER TABLE pool ENABLE ROW LEVEL SECURITY;
ALTER TABLE donations ENABLE ROW LEVEL SECURITY;
ALTER TABLE payouts ENABLE ROW LEVEL SECURITY;

-- Users
CREATE POLICY "Anyone can read users" ON users FOR SELECT USING (TRUE);
CREATE POLICY "Users can update own profile" ON users FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Service role manages users" ON users FOR ALL USING (auth.role() = 'service_role');

-- Repos
CREATE POLICY "Anyone can read repos" ON repos FOR SELECT USING (TRUE);
CREATE POLICY "Service role manages repos" ON repos FOR ALL USING (auth.role() = 'service_role');

-- Contributors
CREATE POLICY "Anyone can read contributors" ON contributors FOR SELECT USING (TRUE);
CREATE POLICY "Service role manages contributors" ON contributors FOR ALL USING (auth.role() = 'service_role');

-- Repo contributors
CREATE POLICY "Anyone can read repo_contributors" ON repo_contributors FOR SELECT USING (TRUE);
CREATE POLICY "Service role manages repo_contributors" ON repo_contributors FOR ALL USING (auth.role() = 'service_role');

-- Pool
CREATE POLICY "Anyone can read pool" ON pool FOR SELECT USING (TRUE);
CREATE POLICY "Service role manages pool" ON pool FOR ALL USING (auth.role() = 'service_role');

-- Donations
CREATE POLICY "Anyone can read donations" ON donations FOR SELECT USING (TRUE);
CREATE POLICY "Authenticated users can donate" ON donations FOR INSERT
    WITH CHECK (auth.role() = 'authenticated' AND donor_id = auth.uid());
CREATE POLICY "Service role manages donations" ON donations FOR ALL USING (auth.role() = 'service_role');

-- Payouts
CREATE POLICY "Contributors can read own payouts" ON payouts FOR SELECT
    USING (contributor_id IN (SELECT id FROM contributors WHERE user_id = auth.uid()));
CREATE POLICY "Service role manages payouts" ON payouts FOR ALL USING (auth.role() = 'service_role');

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

CREATE TRIGGER users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER repos_updated_at BEFORE UPDATE ON repos FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER contributors_updated_at BEFORE UPDATE ON contributors FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER repo_contributors_updated_at BEFORE UPDATE ON repo_contributors FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER pool_updated_at BEFORE UPDATE ON pool FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- HANDLE NEW USER TRIGGER (auto-create user row on Supabase Auth signup)
-- =============================================================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, github_id, github_username, avatar_url, display_name, email)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'provider_id', NEW.id::TEXT),
        COALESCE(NEW.raw_user_meta_data->>'user_name', split_part(NEW.email, '@', 1)),
        NEW.raw_user_meta_data->>'avatar_url',
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'user_name', split_part(NEW.email, '@', 1)),
        NEW.email
    )
    ON CONFLICT (github_id) DO UPDATE SET
        github_username = EXCLUDED.github_username,
        avatar_url = EXCLUDED.avatar_url,
        display_name = EXCLUDED.display_name,
        email = EXCLUDED.email;

    -- Auto-link this user to any existing contributor entry with the same GitHub username
    UPDATE public.contributors
    SET user_id = NEW.id
    WHERE github_username = COALESCE(NEW.raw_user_meta_data->>'user_name', '')
      AND user_id IS NULL;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- =============================================================================
-- SEED: Create initial monthly pool for the current month
-- =============================================================================
INSERT INTO pool (name, description, total_amount_cents, donor_count, status, round_start, round_end)
VALUES (
    to_char(now(), 'FMMonth YYYY') || ' Open Source Fund',
    'Monthly donation pool for ' || to_char(now(), 'FMMonth YYYY') || '. Payouts distributed weekly.',
    0,
    0,
    'active',
    date_trunc('month', now()),
    (date_trunc('month', now()) + interval '1 month' - interval '1 second')
);
