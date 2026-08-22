# Multi-Account & Multi-Member Profile Support

The Garmin HA AI integration natively supports multiple Garmin Connect accounts within a single Home Assistant instance, ensuring complete privacy and isolation between household members.

## Isolation Architecture

1. **Storage Partitioning**:
   - OAuth tokens are saved independently to `.storage/garmin_ha_ai_tokens_{entry_id}.json`.
   - Metric history snapshots are stored in `.storage/garmin_ha_ai_history_{entry_id}.json`.
   - Existing single-account setups seamlessly migrate legacy storage without losing historical data.

2. **Dedicated Device Scope**:
   - Each Garmin Connect account creates its own Home Assistant Device (e.g., `Garmin AI (user@example.com)`).
   - Sensor, button, select, and text entities are strictly namespaced with the `entry_id` to prevent collisions.

3. **Personalized Goals & AI Personas**:
   - Each account maintains distinct fitness goals, target weights, coaching personas, polling times, and notification targets configured in its own Options Flow.

4. **Targeted Service Calls**:
   - Services `garmin_ha_ai.generate_report` and `garmin_ha_ai.ask_question` accept an optional `entry_id` parameter to target specific accounts, or execute globally across all accounts when omitted.
