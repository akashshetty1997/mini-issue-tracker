-- Runs once, when the Postgres volume is first initialised.
-- Creates a separate database so the test suite never touches development data.
CREATE DATABASE issue_tracker_test;
