from typing import Any

from pymongo import ASCENDING, DESCENDING

IndexSpec = tuple[list[tuple[str, int]], dict[str, Any]]

COLLECTION_INDEXES: dict[str, list[IndexSpec]] = {
    "users": [
        ([("email", ASCENDING)], {"unique": True, "name": "uniq_users_email"}),
        ([("google_sub", ASCENDING)], {"unique": True, "sparse": True, "name": "uniq_users_google_sub"}),
        ([("role", ASCENDING)], {"name": "idx_users_role"}),
    ],
    "challenges": [
        ([("created_by", ASCENDING), ("created_at", DESCENDING)], {"name": "idx_challenges_owner_created"}),
        ([("status", ASCENDING), ("category", ASCENDING)], {"name": "idx_challenges_status_category"}),
    ],
    "teams": [
        ([("challenge_id", ASCENDING)], {"name": "idx_teams_challenge"}),
        ([("member_ids", ASCENDING)], {"name": "idx_teams_members"}),
    ],
    "solutions": [
        ([("challenge_id", ASCENDING), ("submitted_at", DESCENDING)], {"name": "idx_solutions_challenge_submitted"}),
        ([("team_id", ASCENDING)], {"name": "idx_solutions_team"}),
    ],
    "reviews": [
        ([("solution_id", ASCENDING)], {"name": "idx_reviews_solution"}),
        ([("reviewer_id", ASCENDING)], {"name": "idx_reviews_reviewer"}),
    ],
    "tasks": [
        ([("team_id", ASCENDING), ("status", ASCENDING)], {"name": "idx_tasks_team_status"}),
        ([("assignee_id", ASCENDING)], {"name": "idx_tasks_assignee"}),
    ],
    "notifications": [
        ([("user_id", ASCENDING), ("created_at", DESCENDING)], {"name": "idx_notifications_user_created"}),
        ([("user_id", ASCENDING), ("is_read", ASCENDING)], {"name": "idx_notifications_user_read"}),
    ],
    "revoked_tokens": [
        ([("jti", ASCENDING)], {"unique": True, "name": "uniq_revoked_tokens_jti"}),
        ([("expires_at", ASCENDING)], {"expireAfterSeconds": 0, "name": "ttl_revoked_tokens_expiry"}),
    ],
}


async def ensure_database_structure(database: Any) -> None:
    for collection_name, indexes in COLLECTION_INDEXES.items():
        collection = database[collection_name]
        for keys, options in indexes:
            await collection.create_index(keys, **options)