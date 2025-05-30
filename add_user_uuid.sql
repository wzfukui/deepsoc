-- 手工为旧版数据库添加 user_id (UUID) 列
-- 为用户表增加字符串类型的 user_id，并填充随机值
ALTER TABLE users ADD COLUMN user_id VARCHAR(64);
UPDATE users SET user_id = UUID() WHERE user_id IS NULL;
ALTER TABLE users MODIFY user_id VARCHAR(64) NOT NULL;
ALTER TABLE users ADD UNIQUE KEY `uix_user_id` (`user_id`);

-- 在消息表中记录发送者的 user_id
ALTER TABLE messages ADD COLUMN user_id VARCHAR(64);
