from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# AGENTCOMMERCE OS - BASELINE INTELLIGENCE EVALUATION
# =============================================================================

BASE_DIR = Path(__file__).resolve().parents[2]
INTELLIGENCE_DIR = BASE_DIR / "data" / "intelligence"
FEATURE_DIR = BASE_DIR / "data" / "features"

BASELINE_FILE = INTELLIGENCE_DIR / "baseline_decisions.csv"
SESSION_FILE = FEATURE_DIR / "session_features.csv"

REQUIRED_COLUMNS = {
	"session_id",
	"opportunity_level",
	"agent_action",
	"purchase_opportunity_score",
	"discount_opportunity_score",
}


def load_baseline():
	if not BASELINE_FILE.exists():
		raise FileNotFoundError(
			f"Baseline file not found: {BASELINE_FILE}\n"
			"Run script/intelligence/baseline_engine.py first."
		)

	decisions = pd.read_csv(BASELINE_FILE)
	missing = REQUIRED_COLUMNS - set(decisions.columns)
	if missing:
		raise ValueError(
			"Baseline file is missing required columns: "
			+ ", ".join(sorted(missing))
		)

	outcome_columns = {"purchased", "effective_price", "quantity"}
	if not outcome_columns.issubset(decisions.columns):
		if not SESSION_FILE.exists():
			raise FileNotFoundError(
				f"Outcome fields are missing and session features were not found: {SESSION_FILE}"
			)

		outcomes = pd.read_csv(
			SESSION_FILE,
			usecols=["session_id", "purchased", "effective_price", "quantity"],
		)
		decisions = decisions.merge(outcomes, on="session_id", how="left")

	decisions["purchased"] = pd.to_numeric(
		decisions["purchased"], errors="coerce"
	).fillna(0).astype(int)
	decisions["effective_price"] = pd.to_numeric(
		decisions["effective_price"], errors="coerce"
	).fillna(0)
	decisions["quantity"] = pd.to_numeric(
		decisions["quantity"], errors="coerce"
	).fillna(0)
	decisions["actual_revenue"] = (
		decisions["purchased"]
		* decisions["effective_price"]
		* decisions["quantity"]
	)
	return decisions


def opportunity_quality(decisions):
	return (
		decisions.groupby("opportunity_level", dropna=False)
		.agg(
			sessions=("session_id", "size"),
			actual_purchases=("purchased", "sum"),
			actual_purchase_rate=("purchased", "mean"),
			average_revenue=("actual_revenue", "mean"),
			total_revenue=("actual_revenue", "sum"),
		)
		.reindex(["LOW", "MEDIUM", "HIGH"])
		.reset_index()
	)


def action_quality(decisions):
	return (
		decisions.groupby("agent_action", dropna=False)
		.agg(
			count=("session_id", "size"),
			purchase_rate=("purchased", "mean"),
			average_revenue=("actual_revenue", "mean"),
		)
		.sort_values("purchase_rate")
		.reset_index()
	)


def score_deciles(decisions, score_column):
	ranked = decisions[[score_column, "purchased"]].copy()
	ranked[score_column] = pd.to_numeric(ranked[score_column], errors="coerce")
	ranked = ranked.dropna(subset=[score_column])

	if ranked.empty:
		raise ValueError(f"No finite values available for {score_column}")

	ranked["decile"] = (
		ranked[score_column]
		.rank(method="first", pct=True)
		.mul(10)
		.apply(np.ceil)
		.clip(1, 10)
		.astype("Int64")
	)

	result = (
		ranked.groupby("decile")
		.agg(
			sessions=("purchased", "size"),
			actual_purchases=("purchased", "sum"),
			actual_purchase_rate=("purchased", "mean"),
			average_score=(score_column, "mean"),
		)
		.reindex(range(1, 11))
		.reset_index()
	)
	result["decile"] = result["decile"].map(lambda value: f"D{int(value)}")
	return result


def discount_policy_analysis(decisions):
	analysis = decisions.copy()
	analysis["customer_intent"] = np.where(
		analysis["session_intent_score"] >= 0.65, "HIGH", "MEDIUM_OR_LOW"
	)
	analysis["product_conversion"] = np.where(
		analysis["product_conversion_score"] >= 0.65, "HIGH", "MEDIUM_OR_LOW"
	)
	analysis["discount_sensitivity"] = np.where(
		analysis["discount_dependence_score"] >= 0.65, "HIGH", "LOW"
	)
	analysis["discount_recommendation"] = np.select(
		[
			(analysis["customer_intent"] == "HIGH")
			& (analysis["product_conversion"] == "HIGH")
			& (analysis["discount_sensitivity"] == "LOW"),
			(analysis["customer_intent"] == "HIGH")
			& (analysis["discount_sensitivity"] == "HIGH"),
		],
		["DONT_DISCOUNT", "CONSIDER_LIMITED_OFFER"],
		default="NO_DISCOUNT_SIGNAL",
	)

	return (
		analysis.groupby("discount_recommendation")
		.agg(
			sessions=("session_id", "size"),
			actual_purchases=("purchased", "sum"),
			actual_purchase_rate=("purchased", "mean"),
			average_revenue=("actual_revenue", "mean"),
		)
		.reset_index()
	)


def print_table(title, table):
	print(f"\n{title}")
	print(table.round(4).to_string(index=False))


def main():
	decisions = load_baseline()
	print("=" * 80)
	print("AGENTCOMMERCE OS - BASELINE INTELLIGENCE EVALUATION")
	print("=" * 80)
	print(f"Baseline sessions: {len(decisions):,}")

	opportunity = opportunity_quality(decisions)
	actions = action_quality(decisions)
	purchase_deciles = score_deciles(decisions, "purchase_opportunity_score")
	discount_deciles = score_deciles(decisions, "discount_opportunity_score")
	discount_policy = discount_policy_analysis(decisions)

	print_table("1. OPPORTUNITY QUALITY", opportunity)
	print_table("2. ACTION QUALITY", actions)
	print_table("3. PURCHASE OPPORTUNITY SCORE DECILES", purchase_deciles)
	print_table("4. DISCOUNT OPPORTUNITY SCORE DECILES", discount_deciles)
	print_table("5. DISCOUNT POLICY ANALYSIS", discount_policy)

	high_rate = opportunity.loc[
		opportunity["opportunity_level"] == "HIGH", "actual_purchase_rate"
	].iloc[0]
	low_rate = opportunity.loc[
		opportunity["opportunity_level"] == "LOW", "actual_purchase_rate"
	].iloc[0]
	print("\nSIGNAL CHECK")
	print(
		"HIGH opportunity has a higher purchase rate: "
		f"{'YES' if high_rate > low_rate else 'NO'} "
		f"(HIGH={high_rate:.2%}, LOW={low_rate:.2%})"
	)

	print("\nINTERPRETATION")
	print(
		"Use the purchase deciles to check whether conversion generally rises "
		"from D1 to D10. Discount deciles are descriptive only; they do not "
		"assume that a higher score means a discount should be offered."
	)


if __name__ == "__main__":
	main()
