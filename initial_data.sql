-- DeepSOC sample data
-- Admin user
INSERT INTO users (id, username, email, password_hash, role, is_active, created_at, updated_at)
VALUES (1, 'admin', 'admin@deepsoc.local', 'scrypt:32768:8:1$HPOVyVMaQEEGKP2o$522a398c23d8113db73d24dd86f417670ccb5dd432f120e26183579d7aeef4741853a6e0dc151da56b4e9b1fde479dd7c67b3d2a9c246c7a24d6c6fe99f3a36c', 'admin', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Example event
INSERT INTO events (id, event_id, event_name, message, context, source, severity, event_status, current_round, created_at, updated_at)
VALUES (1, 'demo-event', 'Demo Security Event', 'Suspicious traffic detected on 66.240.205.34', 'internal server 192.168.22.251', 'SIEM', 'medium', 'processing', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
