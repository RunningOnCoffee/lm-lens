"""
Seed data for the 7 built-in user profiles.

Each profile includes:
- Behavior defaults (session mode, think time, turns)
- Conversation templates with starter prompts
- Follow-up prompts (template-specific and universal)
- Template variables for combinatorial diversity
"""

PROFILES = [
    # -------------------------------------------------------
    # 1. Casual User
    # -------------------------------------------------------
    {
        "slug": "casual-user",
        "name": "Casual User",
        "description": "Short conversational prompts, 1-3 turn sessions. Simulates everyday users asking quick questions, getting recommendations, or having brief chats.",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 1, "max": 3},
            "think_time_seconds": {"min": 3, "max": 15},
            "sessions_per_user": {"min": 1, "max": 5},
            "read_time_factor": 0.01,
        },
        "conversation_templates": [
            {
                "category": "question",
                "starter_prompt": "What's the difference between $TOPIC_A and $TOPIC_B?",
                "expected_response_tokens": {"min": 80, "max": 250},
                "follow_ups": [
                    {"content": "Can you give me a simple example?"},
                    {"content": "Which one would you recommend for a beginner?"},
                ],
            },
            {
                "category": "recommendation",
                "starter_prompt": "I'm looking for a good $ITEM_TYPE for $PURPOSE. Any suggestions?",
                "expected_response_tokens": {"min": 100, "max": 300},
                "follow_ups": [
                    {"content": "What about something cheaper?"},
                    {"content": "How does that compare to $ALTERNATIVE?"},
                ],
            },
            {
                "category": "explanation",
                "starter_prompt": "Explain $CONCEPT to me like I'm 10 years old.",
                "expected_response_tokens": {"min": 100, "max": 250},
                "follow_ups": [
                    {"content": "Why does that matter?"},
                    {"content": "Can you give a real-world example?"},
                ],
            },
            {
                "category": "how-to",
                "starter_prompt": "How do I $TASK?",
                "expected_response_tokens": {"min": 80, "max": 300},
                "follow_ups": [
                    {"content": "What if that doesn't work?"},
                    {"content": "Is there an easier way?"},
                ],
            },
        ],
        "universal_follow_ups": [
            "Thanks! One more question — can you summarize that in one sentence?",
            "Interesting. Tell me more.",
            "Wait, I'm confused. Can you rephrase that?",
        ],
        "template_variables": [
            {"name": "TOPIC_A", "values": ["machine learning", "Python", "REST APIs", "cloud computing", "Docker", "SQL"]},
            {"name": "TOPIC_B", "values": ["deep learning", "JavaScript", "GraphQL", "edge computing", "Kubernetes", "NoSQL"]},
            {"name": "CONCEPT", "values": ["blockchain", "quantum computing", "neural networks", "API rate limiting", "DNS", "encryption"]},
            {"name": "ITEM_TYPE", "values": ["laptop", "programming book", "online course", "code editor", "headset", "monitor"]},
            {"name": "PURPOSE", "values": ["learning to code", "remote work", "gaming", "data science", "web development", "productivity"]},
            {"name": "ALTERNATIVE", "values": ["the previous version", "the open-source option", "the budget option"]},
            {"name": "TASK", "values": ["set up a VPN", "create a budget spreadsheet", "back up my photos", "learn a new language fast", "improve my Wi-Fi signal"]},
        ],
    },

    # -------------------------------------------------------
    # 2. Power User / Researcher
    # -------------------------------------------------------
    {
        "slug": "power-user",
        "name": "Power User / Researcher",
        "description": "Long analytical prompts with multi-paragraph responses. Simulates researchers, analysts, and advanced users who need deep, nuanced answers and engage in extended conversations.",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 5, "max": 15},
            "think_time_seconds": {"min": 15, "max": 60},
            "sessions_per_user": {"min": 1, "max": 2},
            "read_time_factor": 0.03,
        },
        "conversation_templates": [
            {
                "category": "analysis",
                "starter_prompt": "I'm researching $RESEARCH_TOPIC. Can you provide a comprehensive overview of the current state of the field, including the main schools of thought, key recent developments, and open questions that remain unresolved?",
                "expected_response_tokens": {"min": 400, "max": 1200},
                "follow_ups": [
                    {"content": "What are the strongest counterarguments to the dominant position you described?"},
                    {"content": "Can you trace the historical development of this field? What were the key inflection points?"},
                    {"content": "Which methodological approaches have proven most reliable in this area, and why?"},
                    {"content": "How does this intersect with $RELATED_FIELD? Are there cross-disciplinary insights I should be aware of?"},
                ],
            },
            {
                "category": "comparison",
                "starter_prompt": "Compare and contrast $FRAMEWORK_A and $FRAMEWORK_B in terms of their theoretical foundations, practical applications, empirical support, and limitations. I need a balanced, scholarly assessment.",
                "expected_response_tokens": {"min": 500, "max": 1500},
                "follow_ups": [
                    {"content": "Which one has more empirical support in real-world settings?"},
                    {"content": "What would a synthesis of both approaches look like?"},
                    {"content": "Are there notable critics of either framework? What are their main objections?"},
                ],
            },
            {
                "category": "literature-review",
                "starter_prompt": "I'm writing a literature review on $REVIEW_TOPIC. What are the seminal papers and key findings I should be aware of? Please organize them chronologically and note any paradigm shifts.",
                "expected_response_tokens": {"min": 500, "max": 1500},
                "follow_ups": [
                    {"content": "What gaps exist in the current literature that could be addressed by future research?"},
                    {"content": "How has the methodology evolved over time in this field?"},
                    {"content": "Can you suggest a structure for organizing my literature review?"},
                ],
            },
        ],
        "universal_follow_ups": [
            "Let me push back on that. Isn't it true that $COUNTERPOINT? How would you reconcile that with your analysis?",
            "Can you provide specific citations or data points to support that claim?",
            "How confident are you in that assessment? What would change your mind?",
            "Summarize the key takeaways from our entire conversation so far.",
            "Given everything we've discussed, what would you recommend as the most productive next steps for my research?",
        ],
        "template_variables": [
            {"name": "RESEARCH_TOPIC", "values": ["transformer architectures in NLP", "causal inference in observational studies", "the impact of remote work on productivity", "microservices vs monolithic architecture trade-offs", "zero-knowledge proofs in blockchain"]},
            {"name": "RELATED_FIELD", "values": ["cognitive science", "economics", "systems engineering", "information theory", "organizational psychology"]},
            {"name": "FRAMEWORK_A", "values": ["Bayesian inference", "agile methodology", "actor-critic reinforcement learning", "event-driven architecture"]},
            {"name": "FRAMEWORK_B", "values": ["frequentist statistics", "waterfall methodology", "model-based reinforcement learning", "request-response architecture"]},
            {"name": "REVIEW_TOPIC", "values": ["LLM evaluation methods", "distributed consensus algorithms", "human-AI collaboration", "technical debt measurement"]},
            {"name": "COUNTERPOINT", "values": ["recent studies show contradictory results", "the sample sizes in those studies were too small", "the methodology has been questioned"]},
        ],
    },

    # -------------------------------------------------------
    # 3. Programmer
    # -------------------------------------------------------
    {
        "slug": "programmer",
        "name": "Programmer",
        "description": "Code snippets, debugging sessions, and multi-turn refinement. Simulates developers pasting code and asking for improvements, bug fixes, or explanations.",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 3, "max": 10},
            "think_time_seconds": {"min": 10, "max": 60},
            "sessions_per_user": {"min": 1, "max": 3},
            "read_time_factor": 0.03,
        },
        "conversation_templates": [
            {
                "category": "code-review",
                "starter_prompt": "Review this $LANGUAGE code and suggest improvements for readability, performance, and best practices:\n\n```$LANGUAGE\n$CODE_BLOCK\n```",
                "expected_response_tokens": {"min": 300, "max": 800},
                "follow_ups": [
                    {"content": "Can you refactor it using the improvements you suggested? Show me the full updated code."},
                    {"content": "What about error handling? What edge cases am I missing?"},
                    {"content": "How would you write unit tests for this?"},
                    {"content": "Can you add type hints and docstrings?"},
                ],
            },
            {
                "category": "debugging",
                "starter_prompt": "I'm getting an unexpected result from this $LANGUAGE code. The expected output is $EXPECTED_OUTPUT but I'm getting $ACTUAL_OUTPUT. Can you find the bug?\n\n```$LANGUAGE\n$CODE_BLOCK\n```",
                "expected_response_tokens": {"min": 200, "max": 600},
                "follow_ups": [
                    {"content": "That fixed it, but now I'm seeing a performance issue with large inputs. How can I optimize it?"},
                    {"content": "Can you explain why the original code produced the wrong result?"},
                    {"content": "Are there any other potential issues you can spot?"},
                ],
            },
            {
                "category": "implementation",
                "starter_prompt": "Write a $LANGUAGE implementation of $ALGORITHM_OR_FEATURE. It should handle $REQUIREMENTS.",
                "expected_response_tokens": {"min": 300, "max": 1000},
                "follow_ups": [
                    {"content": "Can you add error handling and input validation?"},
                    {"content": "How would you modify this to be thread-safe?"},
                    {"content": "Can you write a version that's more memory-efficient?"},
                    {"content": "Now add logging and make it production-ready."},
                ],
            },
            {
                "category": "explanation",
                "starter_prompt": "Explain what this $LANGUAGE code does step by step. I inherited this from a colleague and need to understand it before modifying it:\n\n```$LANGUAGE\n$CODE_BLOCK\n```",
                "expected_response_tokens": {"min": 300, "max": 800},
                "follow_ups": [
                    {"content": "What design pattern is this using? Is it the right choice here?"},
                    {"content": "If I needed to add $NEW_FEATURE to this, where would I start?"},
                    {"content": "What would break if I removed the $COMPONENT part?"},
                ],
            },
        ],
        "universal_follow_ups": [
            "Can you add comments explaining the non-obvious parts?",
            "What's the time and space complexity of this solution?",
            "Show me an alternative approach.",
            "How would this look in $ALT_LANGUAGE instead?",
        ],
        "template_variables": [
            {"name": "LANGUAGE", "values": ["Python", "JavaScript", "TypeScript", "Go", "Rust", "Java"]},
            {"name": "ALT_LANGUAGE", "values": ["Python", "Go", "Rust", "TypeScript"]},
            {"name": "EXPECTED_OUTPUT", "values": ["a sorted list", "True", "the sum of all values", "a valid JSON object"]},
            {"name": "ACTUAL_OUTPUT", "values": ["an empty list", "False", "None", "a TypeError"]},
            {"name": "ALGORITHM_OR_FEATURE", "values": ["a rate limiter using token bucket", "a LRU cache", "a retry mechanism with exponential backoff", "a connection pool", "a simple pub/sub event system"]},
            {"name": "REQUIREMENTS", "values": ["concurrent access from multiple threads", "graceful error recovery", "configurable timeouts", "memory usage under 100MB"]},
            {"name": "NEW_FEATURE", "values": ["caching", "retry logic", "authentication", "pagination", "streaming support"]},
            {"name": "COMPONENT", "values": ["the middleware", "the validation layer", "the callback", "the context manager"]},
        ],
    },

    # -------------------------------------------------------
    # 4. Content Creator / Marketing
    # -------------------------------------------------------
    {
        "slug": "content-creator",
        "name": "Content Creator / Marketing",
        "description": "Document rewrites, summaries, SEO content, and marketing copy. Simulates content professionals who need polished, structured text output.",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 2, "max": 6},
            "think_time_seconds": {"min": 8, "max": 30},
            "sessions_per_user": {"min": 1, "max": 4},
            "read_time_factor": 0.02,
        },
        "conversation_templates": [
            {
                "category": "blog-post",
                "starter_prompt": "Write a $WORD_COUNT-word blog post about $BLOG_TOPIC targeting $AUDIENCE. Use a $TONE tone and include a compelling introduction, 3-4 key sections with subheadings, and a strong conclusion with a call to action.",
                "expected_response_tokens": {"min": 400, "max": 1200},
                "follow_ups": [
                    {"content": "Make the introduction more engaging — add a hook or surprising statistic."},
                    {"content": "The tone is too formal. Make it more conversational while keeping it professional."},
                    {"content": "Add SEO optimization: suggest a meta description, title tag, and 5 target keywords."},
                    {"content": "Rewrite the conclusion to be more actionable."},
                ],
            },
            {
                "category": "rewrite",
                "starter_prompt": "Rewrite the following text to be more $QUALITY. Keep the core message but improve the $ASPECT:\n\n$SAMPLE_TEXT",
                "expected_response_tokens": {"min": 200, "max": 600},
                "follow_ups": [
                    {"content": "Good, but can you make it about 30% shorter without losing key points?"},
                    {"content": "Now create 3 different versions for A/B testing."},
                    {"content": "Adapt this for a $PLATFORM audience."},
                ],
            },
            {
                "category": "email",
                "starter_prompt": "Write a $EMAIL_TYPE email for $EMAIL_PURPOSE. The target audience is $AUDIENCE and the key message is $KEY_MESSAGE.",
                "expected_response_tokens": {"min": 150, "max": 400},
                "follow_ups": [
                    {"content": "Write 5 different subject line options, ordered from most professional to most creative."},
                    {"content": "Make it more urgent without being pushy."},
                    {"content": "Create a follow-up email for people who didn't open the first one."},
                ],
            },
        ],
        "universal_follow_ups": [
            "Can you create a shorter social media version of this?",
            "Adjust the reading level to be accessible to a wider audience.",
            "Add a section addressing common objections or concerns.",
        ],
        "template_variables": [
            {"name": "BLOG_TOPIC", "values": ["the future of remote work tools", "how to build a personal brand", "AI in content marketing", "developer productivity tips", "open-source business models"]},
            {"name": "AUDIENCE", "values": ["tech professionals", "startup founders", "marketing managers", "small business owners", "engineering teams"]},
            {"name": "TONE", "values": ["professional", "casual and friendly", "authoritative", "inspirational"]},
            {"name": "WORD_COUNT", "values": ["800", "1200", "1500", "2000"]},
            {"name": "QUALITY", "values": ["concise", "engaging", "persuasive", "clear and actionable"]},
            {"name": "ASPECT", "values": ["clarity", "flow", "impact", "structure"]},
            {"name": "SAMPLE_TEXT", "values": [
                "Our company provides solutions that leverage cutting-edge technology to deliver best-in-class results for our valued customers across all verticals. We are committed to excellence and innovation in everything we do, driving transformative outcomes.",
                "The quarterly results show that our team has made significant progress on multiple fronts. Revenue is up 15% year-over-year, customer retention improved by 8 points, and we launched three new products.",
            ]},
            {"name": "PLATFORM", "values": ["LinkedIn", "Twitter/X", "Instagram", "newsletter"]},
            {"name": "EMAIL_TYPE", "values": ["cold outreach", "follow-up", "product announcement", "newsletter"]},
            {"name": "EMAIL_PURPOSE", "values": ["launching a new feature", "re-engaging inactive users", "announcing a webinar", "requesting a meeting"]},
            {"name": "KEY_MESSAGE", "values": ["we save teams 10 hours per week", "early access is now open", "join 500+ companies already using our platform"]},
        ],
    },

    # -------------------------------------------------------
    # 5. Data Analyst
    # -------------------------------------------------------
    {
        "slug": "data-analyst",
        "name": "Data Analyst",
        "description": "CSV/table data, SQL generation, analysis requests, and data interpretation. Simulates analysts who work with structured data and need query help or statistical insights.",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 3, "max": 8},
            "think_time_seconds": {"min": 10, "max": 45},
            "sessions_per_user": {"min": 1, "max": 3},
            "read_time_factor": 0.03,
        },
        "conversation_templates": [
            {
                "category": "sql",
                "starter_prompt": "I have a $DATABASE_TYPE database with the following tables:\n\n$SCHEMA_DESCRIPTION\n\nWrite a SQL query to $QUERY_GOAL.",
                "expected_response_tokens": {"min": 200, "max": 600},
                "follow_ups": [
                    {"content": "How would I optimize this query for a table with 50 million rows?"},
                    {"content": "Can you add a window function to also show the running total?"},
                    {"content": "Now modify it to filter by date range and group by $GROUP_BY."},
                    {"content": "Explain the query plan — where might this be slow?"},
                ],
            },
            {
                "category": "analysis",
                "starter_prompt": "I have the following dataset summary:\n\n$DATA_SUMMARY\n\nWhat are the key insights? What patterns or anomalies do you see? Suggest 3 analyses I should run next.",
                "expected_response_tokens": {"min": 300, "max": 800},
                "follow_ups": [
                    {"content": "How would I test if the trend you identified is statistically significant?"},
                    {"content": "Write Python code using pandas to reproduce this analysis."},
                    {"content": "What visualizations would best communicate these findings to a non-technical stakeholder?"},
                ],
            },
            {
                "category": "transformation",
                "starter_prompt": "I need to transform $SOURCE_FORMAT data into $TARGET_FORMAT. The source data looks like this:\n\n$SAMPLE_DATA\n\nWrite a $TRANSFORM_LANGUAGE script to do the transformation.",
                "expected_response_tokens": {"min": 200, "max": 600},
                "follow_ups": [
                    {"content": "How do I handle missing values and data quality issues?"},
                    {"content": "Add validation to ensure the output matches the expected schema."},
                    {"content": "Now make this work as a scheduled pipeline that runs daily."},
                ],
            },
        ],
        "universal_follow_ups": [
            "Can you add error handling for edge cases like null values and duplicates?",
            "How would I set this up to run automatically on a schedule?",
            "Summarize the methodology so I can include it in my report.",
        ],
        "template_variables": [
            {"name": "DATABASE_TYPE", "values": ["PostgreSQL", "MySQL", "BigQuery", "Snowflake"]},
            {"name": "SCHEMA_DESCRIPTION", "values": [
                "- users (id, name, email, created_at, plan_type)\n- orders (id, user_id, amount, status, created_at)\n- products (id, name, category, price)",
                "- events (id, user_id, event_type, properties JSONB, timestamp)\n- sessions (id, user_id, start_time, end_time, device_type)\n- users (id, signup_date, country, tier)",
            ]},
            {"name": "QUERY_GOAL", "values": ["find the top 10 customers by total spend in the last 90 days", "calculate monthly retention cohorts", "identify users who downgraded their plan after a support ticket", "find products frequently bought together"]},
            {"name": "GROUP_BY", "values": ["month", "category", "region", "user tier"]},
            {"name": "DATA_SUMMARY", "values": [
                "Monthly revenue: Jan $120K, Feb $135K, Mar $128K, Apr $142K, May $155K, Jun $148K. Churn rate has been increasing from 3.2% to 4.1% over the same period. Average deal size decreased from $2,400 to $2,100.",
                "We tracked 50,000 API requests over 24 hours. Median latency: 45ms. P95: 280ms. P99: 1,200ms. Error rate: 2.3%. Peak traffic at 2PM UTC (3x baseline). 68% of errors are timeouts, 22% are 429s, 10% are 500s.",
            ]},
            {"name": "SOURCE_FORMAT", "values": ["CSV", "JSON", "nested JSON API responses", "Excel"]},
            {"name": "TARGET_FORMAT", "values": ["a normalized PostgreSQL schema", "a flat CSV for analysis", "a Parquet file for analytics", "a JSON API response format"]},
            {"name": "SAMPLE_DATA", "values": ["id,name,orders\n1,Alice,\"[{product: 'A', qty: 2}, {product: 'B', qty: 1}]\"\n2,Bob,\"[{product: 'C', qty: 5}]\""]},
            {"name": "TRANSFORM_LANGUAGE", "values": ["Python", "SQL", "dbt"]},
        ],
    },

    # -------------------------------------------------------
    # 6. Customer Support Bot
    # -------------------------------------------------------
    {
        "slug": "support-bot",
        "name": "Customer Support Bot",
        "description": "Short queries with structured responses. Simulates a customer support chatbot handling common questions with quick, formatted answers.",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 2, "max": 5},
            "think_time_seconds": {"min": 2, "max": 10},
            "sessions_per_user": {"min": 2, "max": 6},
            "read_time_factor": 0.01,
        },
        "conversation_templates": [
            {
                "category": "troubleshooting",
                "starter_prompt": "I'm having trouble with $ISSUE. I've already tried $ATTEMPTED_FIX but it didn't work. Can you help?",
                "expected_response_tokens": {"min": 100, "max": 300},
                "follow_ups": [
                    {"content": "That didn't work either. What else can I try?"},
                    {"content": "I followed your steps and now I'm seeing a different error: $ERROR_MESSAGE"},
                    {"content": "Can I speak to a human agent about this?"},
                ],
            },
            {
                "category": "account",
                "starter_prompt": "I need to $ACCOUNT_ACTION. How do I do that?",
                "expected_response_tokens": {"min": 80, "max": 200},
                "follow_ups": [
                    {"content": "Will I lose my data if I do that?"},
                    {"content": "How long will this take to process?"},
                ],
            },
            {
                "category": "billing",
                "starter_prompt": "I was charged $AMOUNT on $DATE but I $BILLING_ISSUE. Can you explain this charge?",
                "expected_response_tokens": {"min": 100, "max": 250},
                "follow_ups": [
                    {"content": "I'd like a refund for this charge."},
                    {"content": "Can you make sure this doesn't happen again next month?"},
                    {"content": "Where can I see my complete billing history?"},
                ],
            },
            {
                "category": "feature",
                "starter_prompt": "Does your product support $FEATURE_REQUEST?",
                "expected_response_tokens": {"min": 80, "max": 200},
                "follow_ups": [
                    {"content": "When is that planned to be available?"},
                    {"content": "Is there a workaround in the meantime?"},
                ],
            },
        ],
        "universal_follow_ups": [
            "Thanks, that solved it!",
            "I'm still having the issue. This is frustrating.",
            "Can you send me a link to the documentation for this?",
        ],
        "template_variables": [
            {"name": "ISSUE", "values": ["logging into my account", "connecting my integration", "slow loading times", "missing data in my dashboard", "emails not being delivered"]},
            {"name": "ATTEMPTED_FIX", "values": ["restarting my browser", "clearing cookies", "resetting my password", "reinstalling the app", "checking my internet connection"]},
            {"name": "ERROR_MESSAGE", "values": ["'Session expired'", "'Permission denied'", "'Rate limit exceeded'", "'Connection timeout'"]},
            {"name": "ACCOUNT_ACTION", "values": ["upgrade my plan", "cancel my subscription", "change my email address", "add another team member", "export all my data"]},
            {"name": "AMOUNT", "values": ["$49.99", "$99.00", "$199.00", "$29.99"]},
            {"name": "DATE", "values": ["March 15th", "last Tuesday", "the 1st of this month"]},
            {"name": "BILLING_ISSUE", "values": ["don't recognize this charge", "was supposed to be on the free plan", "already cancelled last month", "was double-charged"]},
            {"name": "FEATURE_REQUEST", "values": ["SSO with Okta", "bulk data import via CSV", "custom webhook endpoints", "two-factor authentication", "dark mode"]},
        ],
    },

    # -------------------------------------------------------
    # 7. RAG Pipeline Simulator
    # -------------------------------------------------------
    {
        "slug": "rag-pipeline",
        "name": "RAG Pipeline Simulator",
        "description": "Large context blocks with long-context testing. Simulates retrieval-augmented generation workloads where large documents are injected into the prompt context.",
        "behavior_defaults": {
            "session_mode": "single_shot",
            "turns_per_session": {"min": 1, "max": 2},
            "think_time_seconds": {"min": 1, "max": 5},
            "sessions_per_user": {"min": 3, "max": 10},
            "read_time_factor": 0.01,
        },
        "conversation_templates": [
            {
                "category": "document-qa",
                "starter_prompt": "Based on the following document, answer the question below.\n\n---\nDOCUMENT:\n$DOCUMENT_BLOCK\n---\n\nQUESTION: $DOC_QUESTION",
                "expected_response_tokens": {"min": 100, "max": 400},
                "follow_ups": [
                    {"content": "What parts of the document are most relevant to your answer? Quote them directly."},
                ],
            },
            {
                "category": "summarization",
                "starter_prompt": "Summarize the following document in $SUMMARY_LENGTH. Focus on $SUMMARY_FOCUS.\n\n---\n$DOCUMENT_BLOCK\n---",
                "expected_response_tokens": {"min": 150, "max": 500},
                "follow_ups": [
                    {"content": "Now create 5 bullet-point key takeaways from this document."},
                ],
            },
            {
                "category": "multi-doc",
                "starter_prompt": "I have two documents. Compare them and identify areas of agreement and contradiction.\n\nDOCUMENT A:\n$DOCUMENT_BLOCK\n\nDOCUMENT B:\n$DOCUMENT_BLOCK_B\n\nProvide a structured comparison.",
                "expected_response_tokens": {"min": 300, "max": 800},
                "follow_ups": [
                    {"content": "Which document appears more reliable, and why?"},
                ],
            },
        ],
        "universal_follow_ups": [
            "How confident are you in this answer based on the provided context?",
            "Is there anything important that the document doesn't cover?",
        ],
        "template_variables": [
            {"name": "DOC_QUESTION", "values": [
                "What are the main risks identified in the report?",
                "What recommendations does the author make?",
                "What data supports the main conclusion?",
                "How does this compare to the previous quarter's results?",
            ]},
            {"name": "SUMMARY_LENGTH", "values": ["3-5 sentences", "one paragraph", "200 words", "a single sentence"]},
            {"name": "SUMMARY_FOCUS", "values": ["actionable recommendations", "key metrics and numbers", "risks and mitigations", "strategic implications"]},
            {"name": "DOCUMENT_BLOCK", "values": [
                "Q3 2024 Performance Review\n\nExecutive Summary: The platform processed 12.4 million requests in Q3, up 34% from Q2. Average latency improved from 180ms to 142ms following the migration to the new edge infrastructure. However, error rates increased from 0.3% to 0.7%, primarily due to three incidents in September related to database connection pool exhaustion.\n\nKey Metrics:\n- Total requests: 12.4M (Q2: 9.2M)\n- Average latency: 142ms (Q2: 180ms)\n- P99 latency: 890ms (Q2: 1,240ms)\n- Error rate: 0.7% (Q2: 0.3%)\n- Uptime: 99.91% (Q2: 99.97%)\n\nIncident Summary:\n- Sept 3: 45-minute outage due to connection pool exhaustion during traffic spike. Root cause: missing connection timeout configuration. Fix: implemented adaptive pool sizing.\n- Sept 12: 20-minute degradation in EU region. Root cause: DNS propagation delay after CDN config change. Fix: implemented canary DNS changes.\n- Sept 28: 15-minute elevated error rates. Root cause: third-party payment API degradation. Fix: implemented circuit breaker pattern.\n\nInfrastructure Changes:\n- Migrated 80% of traffic to edge nodes (target: 100% by Q4)\n- Deployed new caching layer reducing database load by 40%\n- Implemented automated scaling policies based on request queue depth\n\nRecommendations:\n1. Complete edge migration by end of Q4\n2. Implement chaos engineering program to proactively identify failure modes\n3. Establish error budget policy: 0.5% error rate threshold triggers deployment freeze\n4. Invest in observability: distributed tracing coverage currently at 60%, target 95%",
                "Technical Architecture Decision Record: Event-Driven Migration\n\nStatus: Approved\nDate: 2024-08-15\nDeciders: Platform Team, Architecture Board\n\nContext:\nOur current synchronous request-response architecture is hitting scalability limits. Peak traffic causes cascading failures as downstream services become overwhelmed. The monolithic message processing pipeline cannot be independently scaled.\n\nDecision:\nMigrate from synchronous HTTP-based inter-service communication to an event-driven architecture using Apache Kafka as the central message broker.\n\nConsequences:\nPositive:\n- Services can be scaled independently based on their queue depth\n- Natural backpressure handling prevents cascading failures\n- Event sourcing enables temporal queries and audit trails\n- Loose coupling allows teams to deploy independently\n\nNegative:\n- Increased operational complexity (Kafka cluster management)\n- Eventual consistency requires changes to UX patterns\n- Debugging distributed event flows is harder than tracing HTTP calls\n- Team needs training on event-driven patterns\n\nMigration Plan:\nPhase 1 (Q4 2024): Set up Kafka infrastructure, migrate notification service\nPhase 2 (Q1 2025): Migrate order processing pipeline\nPhase 3 (Q2 2025): Migrate real-time analytics pipeline\nPhase 4 (Q3 2025): Decommission legacy message queue\n\nRisk Mitigations:\n- Run dual-write during migration phases\n- Implement dead letter queues for failed message processing\n- Deploy schema registry to prevent breaking changes\n- Establish SLOs for event processing latency",
            ]},
            {"name": "DOCUMENT_BLOCK_B", "values": [
                "Alternative Assessment: Microservices Communication\n\nAfter evaluating both event-driven and synchronous approaches, this report recommends a hybrid model. Pure event-driven architecture introduces unnecessary complexity for our current scale. Instead, we should:\n\n1. Keep synchronous communication for real-time user-facing requests\n2. Use events only for background processing and analytics\n3. Implement API gateway with circuit breakers for resilience\n4. Invest in service mesh (Istio) for observability and traffic management\n\nThe estimated implementation cost for the hybrid approach is 40% lower than full event-driven migration, with 80% of the reliability benefits.",
            ]},
        ],
    },
]
