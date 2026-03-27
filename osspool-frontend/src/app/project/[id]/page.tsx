"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getProject, listPools } from "@/lib/api";
import { Project, Pool } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DonateButton } from "@/components/project/donate-button";
import { PoolProgress } from "@/components/pool/pool-progress";
import { formatNumber } from "@/lib/utils";

export default function ProjectPage() {
  const params = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [pools, setPools] = useState<Pool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.id) return;
    setLoading(true);
    setError(null);
    Promise.all([
      getProject(params.id as string),
      listPools("active"),
    ])
      .then(([proj, poolsData]) => {
        setProject(proj);
        setPools(poolsData.pools || []);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load project");
      })
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return (
      <div className="container py-20 flex justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container py-20 text-center text-destructive">
        {error}
      </div>
    );
  }

  if (!project) {
    return (
      <div className="container py-20 text-center text-muted-foreground">
        Project not found
      </div>
    );
  }

  const activePool = pools[0];

  return (
    <div className="container py-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold">{project.name}</h1>
              {project.language && <Badge variant="secondary">{project.language}</Badge>}
            </div>
            {project.description && (
              <p className="text-muted-foreground text-lg">{project.description}</p>
            )}
            <a
              href={project.github_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary hover:underline mt-2 inline-block"
            >
              {project.github_url.replace("https://github.com/", "")}
            </a>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: "Stars", value: formatNumber(project.stars) },
              { label: "Forks", value: formatNumber(project.forks) },
              { label: "Watchers", value: formatNumber(project.watchers) },
              { label: "Open Issues", value: formatNumber(project.open_issues) },
              { label: "Dependents", value: formatNumber(project.dependents_count) },
              { label: "Commits/Week", value: (project.commit_frequency ?? 0).toFixed(1) },
            ].map((stat) => (
              <Card key={stat.label}>
                <CardContent className="pt-4 pb-4">
                  <div className="text-2xl font-bold">{stat.value}</div>
                  <div className="text-xs text-muted-foreground">{stat.label}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Fund This Project</CardTitle>
            </CardHeader>
            <CardContent>
              <DonateButton
                projectId={project.id}
                poolId={activePool?.id}
              />
              {!activePool && (
                <p className="text-sm text-muted-foreground mt-3 text-center">
                  No active funding pool at the moment
                </p>
              )}
            </CardContent>
          </Card>

          {activePool && <PoolProgress pool={activePool} />}
        </div>
      </div>
    </div>
  );
}
