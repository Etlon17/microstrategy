import pandas as pd
import matplotlib.pyplot as plt

# Load the merged DataFrame (adjust the path if needed)
csv_file = "alphavantage_data/analysis_merged_data.csv"
merged_df = pd.read_csv(csv_file, index_col=0, parse_dates=True)

# Define shares outstanding manually (if not included in your CSV)
shares_outstanding = 240_816_000  # adjust this value as needed

# Compute Market Cap if not already computed.
if "market_cap_usd" not in merged_df.columns:
    merged_df["market_cap_usd"] = merged_df["MSTR_market_price"] * shares_outstanding

# Scale Market Cap and NAV_total to billions.
merged_df["market_cap_billion"] = merged_df["market_cap_usd"] / 1e9
merged_df["nav_billion"] = merged_df["NAV_total"] / 1e9

# Create a dual-axis plot.
fig, ax1 = plt.subplots(figsize=(12, 6))

# Plot Market Cap and NAV on primary y-axis.
ax1.plot(merged_df.index, merged_df["nav_billion"], label="NAV (Billion USD)", color="green", linewidth=2)
ax1.plot(merged_df.index, merged_df["market_cap_billion"], label="Market Cap (Billion USD)", color="black", linewidth=2)
ax1.fill_between(
    merged_df.index,
    merged_df["nav_billion"],
    merged_df["market_cap_billion"],
    where=(merged_df["market_cap_billion"] > merged_df["nav_billion"]),
    color="red",
    alpha=0.3,
    label="Premium Zone"
)
ax1.set_xlabel("Date")
ax1.set_ylabel("Billion USD")
ax1.legend(loc="upper left")
ax1.grid(True)

# Create secondary y-axis for BTC price.
ax2 = ax1.twinx()
ax2.plot(merged_df.index, merged_df["BTC_USD_Close"], label="BTC Price", color="yellow", linestyle="--", linewidth=2)
ax2.set_ylabel("BTC Price (USD)")
ax2.legend(loc="upper right")

plt.title("MSTR Market Cap vs. NAV and BTC Price Over Time")
plt.tight_layout()
plt.show()
