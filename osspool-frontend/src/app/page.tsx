import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HomePage() {
  return (
    <div className="flex flex-col">
      <section className="container flex flex-col items-center justify-center gap-6 py-24 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
          Fund the Open Source
          <br />
          <span className="text-primary">That Powers Everything</span>
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          OSSPool ranks critical open-source projects by real impact metrics and
          distributes funding through quadratic funding pools — where many small
          donations have outsized impact.
        </p>
        <div className="flex gap-4">
          <Link href="/leaderboard">
            <Button size="lg">View Leaderboard</Button>
          </Link>
          <Link href="/leaderboard#donate">
            <Button size="lg" variant="outline">
              Start Donating
            </Button>
          </Link>
        </div>
      </section>

      <section className="container py-16">
        <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Discover & Rank</CardTitle>
            </CardHeader>
            <CardContent className="text-muted-foreground">
              Projects are scored by dependents, download velocity, commit
              recency, issue responsiveness, and community growth — updated
              continuously.
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quadratic Funding</CardTitle>
            </CardHeader>
            <CardContent className="text-muted-foreground">
              Your donation is amplified by a matching pool. The more individual
              donors a project has, the larger its matched share — incentivizing
              broad community support.
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Direct Payouts</CardTitle>
            </CardHeader>
            <CardContent className="text-muted-foreground">
              Maintainers connect Stripe to receive funds directly. No
              intermediaries, no delays — money goes straight to the people
              building the tools you depend on.
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="container py-16 border-t">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {[
            { label: "Projects Tracked", value: "2,500+" },
            { label: "Funding Distributed", value: "$1.2M+" },
            { label: "Active Donors", value: "8,400+" },
            { label: "Maintainers Paid", value: "620+" },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-3xl font-bold text-primary">{stat.value}</div>
              <div className="text-sm text-muted-foreground mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
