import type { RecommendationItem } from '~/types/api'
import { getCategoryScore, recommendationCategories } from '~/utils/recommendationConfig'

export type ResultDeltaExplanation = {
  summary: string
  strengths: Array<{ label: string; difference: number }>
  weaknesses: Array<{ label: string; difference: number }>
}

export function buildResultDeltaExplanation(
  item: RecommendationItem,
  reference: RecommendationItem | null
): ResultDeltaExplanation | null {
  if (!reference) {
    return null
  }

  const deltas = recommendationCategories
    .map((category) => ({
      label: category.label,
      difference: getCategoryScore(item, category.key) - getCategoryScore(reference, category.key)
    }))
    .filter((entry) => Math.abs(entry.difference) >= 1)
    .sort((left, right) => Math.abs(right.difference) - Math.abs(left.difference))

  if (!deltas.length) {
    return {
      summary: `${item.name} und ${reference.name} liegen fachlich sehr nah beieinander. Der Abstand entsteht aus vielen kleinen Unterschieden statt aus einem klaren Treiber.`,
      strengths: [],
      weaknesses: []
    }
  }

  const strengths = deltas.filter((entry) => entry.difference > 0).slice(0, 3)
  const weaknesses = deltas.filter((entry) => entry.difference < 0).slice(0, 2)
  const strongest = strengths[0]
  const weakerText = weaknesses.length
    ? ` Schwächer ist ${item.name} bei ${joinLabels(weaknesses.map((entry) => entry.label))}.`
    : ''

  const summary = strongest
    ? `${item.name} liegt vor ${reference.name} vor allem wegen besserer Werte bei ${strongest.label}.${weakerText}`
    : `${item.name} liegt trotz schwächerer Einzelwerte nah an ${reference.name}; die gewichtete Gesamtsicht gleicht die Unterschiede teilweise aus.`

  return {
    summary,
    strengths,
    weaknesses
  }
}

function joinLabels(labels: string[]) {
  if (labels.length <= 1) {
    return labels[0] || ''
  }
  return `${labels.slice(0, -1).join(', ')} und ${labels[labels.length - 1]}`
}
