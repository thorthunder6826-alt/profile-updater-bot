## Packages
recharts | Dashboard analytics and activity charts
framer-motion | Smooth page transitions and UI animations
date-fns | Formatting timestamps for logs and user activity
clsx | Conditional class merging (utility)
tailwind-merge | Class merging (utility)

## Notes
API endpoints inferred from schema:
- GET /api/users - List all telegram users
- GET /api/logs - List activity logs
- POST /api/users - Manually add a user (for testing)
- DELETE /api/users/:id - Remove a user
Dashboard will use mock data for "Bot Status" until real-time websocket is implemented.
