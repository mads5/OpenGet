-- =============================================================================
-- Scoring & Pool Distribution Redesign
-- - Add repo_score to repos
-- - Add total_contributions to contributors
-- - Create monthly_contributor_stats for per-month PR tracking
-- - Create weekly_distributions for audit trail
-- - Extend pool table for dual-pool lifecycle and platform fee
-- =============================================================================

-- ---- repos ----
ALTER TABLE repos ADD COLUMN IF NOT EXISTS repo_score INTEGER DEFAULT 0;

-- ---- contributors ----
ALTER TABLE contributors ADD COLUMN IF NOT EXISTS total_contributions INTEGER DEFAULT 0;

-- ---- pool extensions ----
ALTER TABLE pool ADD COLUMN IF NOT EXISTS platform_fee_cents INTEGER DEFAULT 0;
ALTER TABLE pool ADD COLUMN IF NOT EXISTS daily_budget_cents INTEGER DEFAULT 0;
ALTER TABLE pool ADD COLUMN IF NOT EXISTS remaining_cents INTEGER DEFAULT 0;

ALTER TABLE pool DROP CONSTRAINT IF EXISTS pool_status_check;
ALTER TABLE pool ADD CONSTRAINT pool_status_check
    CHECK (status IN ('collecting', 'active', 'distributing', 'completed'));

-- ---- monthly_contributor_stats ----
CREATE TABLE IF NOT EXISTS monthly_contributor_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contributor_id UUID NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    repo_id UUID NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    month TEXT NOT NULL,  -- 'YYYY-MM'
    prs_raised INTEGER DEFAULT 0 CHECK (prs_raised >= 0),
    prs_merged INTEGER DEFAULT 0 CHECK (prs_merged >= 0),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(contributor_id, repo_id, month)
);

CREATE INDEX IF NOT EXISTS idx_mcs_contributor ON monthly_contributor_stats(contributor_id);
CREATE INDEX IF NOT EXISTS idx_mcs_month ON monthly_contributor_stats(month);
CREATE INDEX IF NOT EXISTS idx_mcs_repo ON monthly_contributor_stats(repo_id);

-- ---- weekly_distributions ----
CREATE TABLE IF NOT EXISTS weekly_distributions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pool_id UUID NOT NULL REFERENCES pool(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    budget_cents INTEGER NOT NULL DEFAULT 0 CHECK (budget_cents >= 0),
    distributed_cents INTEGER NOT NULL DEFAULT 0 CHECK (distributed_cents >= 0),
    is_month_end BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'distributed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wd_pool ON weekly_distributions(pool_id);
CREATE INDEX IF NOT EXISTS idx_wd_status ON weekly_distributions(status);

-- ---- RLS for new tables ----
ALTER TABLE monthly_contributor_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_distributions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read monthly_contributor_stats"
    ON monthly_contributor_stats FOR SELECT USING (TRUE);
CREATE POLICY "Service role manages monthly_contributor_stats"
    ON monthly_contributor_stats FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Anyone can read weekly_distributions"
    ON weekly_distributions FOR SELECT USING (TRUE);
CREATE POLICY "Service role manages weekly_distributions"
    ON weekly_distributions FOR ALL USING (auth.role() = 'service_role');

-- ---- Trigger: auto-update updated_at for monthly_contributor_stats ----
CREATE TRIGGER mcs_updated_at
    BEFORE UPDATE ON monthly_contributor_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
