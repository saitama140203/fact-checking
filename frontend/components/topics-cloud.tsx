"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { TrendingTopic } from "@/lib/api"

interface TopicsCloudProps {
  topics: TrendingTopic[]
  title?: string
  description?: string
}

export function TopicsCloud({ topics, title = "Chủ đề tin giả nổi bật", description }: TopicsCloudProps) {
  const maxFreq = Math.max(...topics.map((t) => t.frequency))

  return (
    <Card className="bg-card">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {topics.map((topic) => {
            const size = (topic.frequency / maxFreq) * 100
            const isHot = size > 70
            const isMedium = size > 40 && size <= 70

            return (
              <Badge
                key={topic.keyword}
                variant="outline"
                className={cn(
                  "cursor-pointer transition-colors",
                  isHot
                    ? "bg-danger/20 text-danger border-danger/30 text-base px-3 py-1"
                    : isMedium
                      ? "bg-warning/20 text-warning border-warning/30"
                      : "bg-muted text-muted-foreground",
                )}
                title={`${topic.frequency} occurrences`}
              >
                {topic.keyword}
                <span className="ml-1 text-xs opacity-70">({topic.frequency})</span>
              </Badge>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ")
}
