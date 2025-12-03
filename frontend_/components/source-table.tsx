"use client"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { SourceCredibility } from "@/lib/api"

interface SourceTableProps {
  sources: SourceCredibility[]
  title: string
  description?: string
  type: "credible" | "warning"
}

const riskBadgeStyles = {
  LOW: "bg-success/20 text-success border-success/30",
  MEDIUM: "bg-warning/20 text-warning border-warning/30",
  HIGH: "bg-chart-4/20 text-chart-4 border-chart-4/30",
  VERY_HIGH: "bg-danger/20 text-danger border-danger/30",
}

export function SourceTable({ sources, title, description, type }: SourceTableProps) {
  return (
    <Card className="bg-card">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-muted-foreground">Tên miền</TableHead>
              <TableHead className="text-muted-foreground text-right">
                {type === "credible" ? "Điểm tin cậy" : "% tin giả"}
              </TableHead>
              <TableHead className="text-muted-foreground text-right">Số bài</TableHead>
              <TableHead className="text-muted-foreground">Mức rủi ro</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sources.map((source) => (
              <TableRow key={source.domain} className="border-border">
                <TableCell className="font-medium">{source.domain}</TableCell>
                <TableCell className="text-right">
                  {type === "credible"
                    ? `${(source.credibility_score ?? 0).toFixed(1)}%`
                    : (() => {
                        // Safely get fake percentage with proper fallback
                        const breakdown = source.breakdown
                        if (!breakdown) return "0.0%"
                        
                        // Prefer fake_percentage if available (0-100)
                        if (typeof breakdown.fake_percentage === "number") {
                          return `${breakdown.fake_percentage.toFixed(1)}%`
                        }
                        
                        // Fallback to fake_ratio (0-1) converted to percentage
                        if (typeof breakdown.fake_ratio === "number") {
                          return `${(breakdown.fake_ratio * 100).toFixed(1)}%`
                        }
                        
                        return "0.0%"
                      })()}
                </TableCell>
                <TableCell className="text-right">{source.breakdown?.total_posts ?? 0}</TableCell>
                <TableCell>
                  <Badge variant="outline" className={cn("border", riskBadgeStyles[source.risk_level])}>
                    {source.risk_level}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
