-- MPU-6050 Test Results Database Schema
-- Author: Murray Kopit <murr2k@gmail.com>
--
-- This SQL script initializes the PostgreSQL database for storing
-- E2E test results, performance metrics, and test history.

-- Create database extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Test executions table
CREATE TABLE IF NOT EXISTS test_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    test_mode VARCHAR(50) NOT NULL,
    environment VARCHAR(50) NOT NULL DEFAULT 'docker',
    git_commit VARCHAR(40),
    git_branch VARCHAR(100),
    build_number INTEGER,
    overall_result VARCHAR(20) NOT NULL CHECK (overall_result IN ('PASSED', 'FAILED', 'TIMEOUT', 'ERROR')),
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    test_duration_seconds DECIMAL(10,3),
    configuration JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Individual test results table
CREATE TABLE IF NOT EXISTS test_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
    test_name VARCHAR(200) NOT NULL,
    test_category VARCHAR(100),
    test_type VARCHAR(50) NOT NULL CHECK (test_type IN ('unit', 'integration', 'e2e', 'performance')),
    result VARCHAR(20) NOT NULL CHECK (result IN ('PASS', 'FAIL', 'SKIP', 'TIMEOUT', 'ERROR')),
    duration_ms INTEGER,
    error_message TEXT,
    test_output TEXT,
    test_data JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_category VARCHAR(50),
    metric_value DECIMAL(15,6) NOT NULL,
    metric_unit VARCHAR(20),
    threshold_min DECIMAL(15,6),
    threshold_max DECIMAL(15,6),
    status VARCHAR(20) CHECK (status IN ('OK', 'WARNING', 'CRITICAL')),
    measurement_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Coverage data table
CREATE TABLE IF NOT EXISTS coverage_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL,
    total_lines INTEGER NOT NULL,
    covered_lines INTEGER NOT NULL,
    coverage_percentage DECIMAL(5,2) NOT NULL,
    branches_total INTEGER DEFAULT 0,
    branches_covered INTEGER DEFAULT 0,
    branch_coverage_percentage DECIMAL(5,2) DEFAULT 0,
    functions_total INTEGER DEFAULT 0,
    functions_covered INTEGER DEFAULT 0,
    function_coverage_percentage DECIMAL(5,2) DEFAULT 0,
    coverage_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- System information table
CREATE TABLE IF NOT EXISTS system_info (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
    hostname VARCHAR(100),
    os_name VARCHAR(50),
    os_version VARCHAR(100),
    kernel_version VARCHAR(100),
    architecture VARCHAR(50),
    cpu_count INTEGER,
    memory_total_mb INTEGER,
    disk_space_mb INTEGER,
    docker_version VARCHAR(100),
    environment_vars JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Error logs table
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID REFERENCES test_executions(id) ON DELETE CASCADE,
    test_result_id UUID REFERENCES test_results(id) ON DELETE CASCADE,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL')),
    component VARCHAR(100),
    message TEXT NOT NULL,
    stack_trace TEXT,
    context JSONB,
    log_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_test_executions_date ON test_executions(execution_date);
CREATE INDEX IF NOT EXISTS idx_test_executions_result ON test_executions(overall_result);
CREATE INDEX IF NOT EXISTS idx_test_executions_branch ON test_executions(git_branch);
CREATE INDEX IF NOT EXISTS idx_test_executions_build ON test_executions(build_number);

CREATE INDEX IF NOT EXISTS idx_test_results_execution ON test_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_test_results_name ON test_results(test_name);
CREATE INDEX IF NOT EXISTS idx_test_results_result ON test_results(result);
CREATE INDEX IF NOT EXISTS idx_test_results_type ON test_results(test_type);

CREATE INDEX IF NOT EXISTS idx_performance_execution ON performance_metrics(execution_id);
CREATE INDEX IF NOT EXISTS idx_performance_name ON performance_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_performance_time ON performance_metrics(measurement_time);

CREATE INDEX IF NOT EXISTS idx_coverage_execution ON coverage_data(execution_id);
CREATE INDEX IF NOT EXISTS idx_coverage_file ON coverage_data(file_path);

CREATE INDEX IF NOT EXISTS idx_error_logs_execution ON error_logs(execution_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs(severity);
CREATE INDEX IF NOT EXISTS idx_error_logs_time ON error_logs(log_time);

-- Create views for common queries
CREATE OR REPLACE VIEW test_summary AS
SELECT 
    te.id,
    te.execution_date,
    te.test_mode,
    te.environment,
    te.git_branch,
    te.overall_result,
    te.total_tests,
    te.passed_tests,
    te.failed_tests,
    ROUND((te.passed_tests::DECIMAL / NULLIF(te.total_tests, 0)) * 100, 2) as pass_rate,
    te.test_duration_seconds,
    COUNT(tr.id) as detailed_test_count,
    COUNT(tr.id) FILTER (WHERE tr.result = 'PASS') as detailed_passed,
    COUNT(tr.id) FILTER (WHERE tr.result = 'FAIL') as detailed_failed
FROM test_executions te
LEFT JOIN test_results tr ON te.id = tr.execution_id
GROUP BY te.id, te.execution_date, te.test_mode, te.environment, 
         te.git_branch, te.overall_result, te.total_tests, 
         te.passed_tests, te.failed_tests, te.test_duration_seconds
ORDER BY te.execution_date DESC;

CREATE OR REPLACE VIEW performance_trends AS
SELECT 
    pm.metric_name,
    pm.metric_unit,
    te.execution_date,
    te.git_branch,
    pm.metric_value,
    AVG(pm.metric_value) OVER (
        PARTITION BY pm.metric_name 
        ORDER BY te.execution_date 
        ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) as moving_average,
    pm.status,
    pm.threshold_min,
    pm.threshold_max
FROM performance_metrics pm
JOIN test_executions te ON pm.execution_id = te.id
ORDER BY pm.metric_name, te.execution_date DESC;

CREATE OR REPLACE VIEW coverage_trends AS
SELECT 
    cd.file_path,
    te.execution_date,
    te.git_branch,
    cd.coverage_percentage,
    cd.branch_coverage_percentage,
    cd.function_coverage_percentage,
    AVG(cd.coverage_percentage) OVER (
        PARTITION BY cd.file_path 
        ORDER BY te.execution_date 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) as avg_coverage_trend
FROM coverage_data cd
JOIN test_executions te ON cd.execution_id = te.id
ORDER BY cd.file_path, te.execution_date DESC;

-- Create functions for common operations
CREATE OR REPLACE FUNCTION get_latest_test_results(limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    execution_id UUID,
    execution_date TIMESTAMP WITH TIME ZONE,
    test_mode VARCHAR,
    result VARCHAR,
    pass_rate NUMERIC,
    duration_seconds NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        te.id,
        te.execution_date,
        te.test_mode,
        te.overall_result,
        ROUND((te.passed_tests::DECIMAL / NULLIF(te.total_tests, 0)) * 100, 2),
        te.test_duration_seconds
    FROM test_executions te
    ORDER BY te.execution_date DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_test_failure_analysis(days_back INTEGER DEFAULT 7)
RETURNS TABLE (
    test_name VARCHAR,
    failure_count BIGINT,
    total_runs BIGINT,
    failure_rate NUMERIC,
    latest_error TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tr.test_name,
        COUNT(*) FILTER (WHERE tr.result = 'FAIL') as failure_count,
        COUNT(*) as total_runs,
        ROUND((COUNT(*) FILTER (WHERE tr.result = 'FAIL')::DECIMAL / COUNT(*)) * 100, 2) as failure_rate,
        (SELECT error_message FROM test_results tr2 
         WHERE tr2.test_name = tr.test_name AND tr2.result = 'FAIL' 
         ORDER BY tr2.completed_at DESC LIMIT 1) as latest_error
    FROM test_results tr
    JOIN test_executions te ON tr.execution_id = te.id
    WHERE te.execution_date >= CURRENT_TIMESTAMP - INTERVAL '%s days'
    GROUP BY tr.test_name
    HAVING COUNT(*) FILTER (WHERE tr.result = 'FAIL') > 0
    ORDER BY failure_rate DESC, failure_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Insert initial configuration data
INSERT INTO test_executions (
    test_mode, 
    environment, 
    overall_result, 
    total_tests, 
    passed_tests, 
    failed_tests,
    test_duration_seconds,
    configuration
) VALUES (
    'initialization',
    'docker',
    'PASSED',
    1,
    1,
    0,
    0.001,
    '{"note": "Database initialized successfully", "version": "1.0.0"}'
) ON CONFLICT DO NOTHING;

-- Grant permissions to testuser
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO testuser;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO testuser;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO testuser;

-- Set up row level security (optional)
-- ALTER TABLE test_executions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE test_results ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE coverage_data ENABLE ROW LEVEL SECURITY;

-- Create a user for read-only dashboard access
CREATE USER dashboard_reader WITH PASSWORD 'dashboard_readonly_123';
GRANT CONNECT ON DATABASE mpu6050_test_results TO dashboard_reader;
GRANT USAGE ON SCHEMA public TO dashboard_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dashboard_reader;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO dashboard_reader;

-- Create test data cleanup function (for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_test_data(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete old test executions and related data (CASCADE will handle related tables)
    WITH deleted AS (
        DELETE FROM test_executions 
        WHERE execution_date < CURRENT_TIMESTAMP - INTERVAL '%s days'
        AND overall_result != 'FAILED'  -- Keep failed tests longer for analysis
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    -- Also delete very old failed tests (older than 90 days)
    WITH deleted_failed AS (
        DELETE FROM test_executions 
        WHERE execution_date < CURRENT_TIMESTAMP - INTERVAL '90 days'
        RETURNING id
    )
    SELECT deleted_count + COUNT(*) INTO deleted_count FROM deleted_failed;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create statistics update function
CREATE OR REPLACE FUNCTION update_table_statistics()
RETURNS VOID AS $$
BEGIN
    ANALYZE test_executions;
    ANALYZE test_results;
    ANALYZE performance_metrics;
    ANALYZE coverage_data;
    ANALYZE error_logs;
END;
$$ LANGUAGE plpgsql;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'MPU-6050 test database schema initialized successfully';
    RAISE NOTICE 'Tables created: test_executions, test_results, performance_metrics, coverage_data, system_info, error_logs';
    RAISE NOTICE 'Views created: test_summary, performance_trends, coverage_trends';
    RAISE NOTICE 'Functions created: get_latest_test_results, get_test_failure_analysis, cleanup_old_test_data, update_table_statistics';
    RAISE NOTICE 'Users created: testuser (full access), dashboard_reader (read-only)';
END $$;