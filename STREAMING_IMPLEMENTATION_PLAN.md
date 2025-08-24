# Streaming Implementation Plan for Agent Execution

## Current Status: Starting Implementation
**Last Updated:** 2024-08-24
**Current Checkpoint:** Starting Checkpoint 1

## Architecture Decision
Using **Progressive Enhancement** approach:
- Phase 1: Internal streaming with enhanced polling (no breaking changes)
- Phase 2: SSE endpoint for real-time streaming (optional enhancement)
- NOT using WebSockets (overkill for one-way streaming)

## Implementation Checkpoints

### ✅ Checkpoint 1: TaskStore with Log Accumulation
**Files to modify:** `services/task_store.py`, `compute/base_agent.py`

**Implementation:**
1. Add log fields to TaskInfo dataclass:
   - `logs: List[str]` - accumulated log lines
   - `log_size: int` - track total size
   - `max_log_size: int = 10_000_000` - 10MB limit
   - `truncated: bool` - flag if logs were truncated

2. Add `append_logs()` method to TaskStore

3. Update `get()` method in base_agent.py to include logs in response

**Test Command:**
```bash
make down && make build && make up
curl -X POST http://localhost:8080/api/v1/operations \
  -H "Content-Type: application/json" \
  -d '{"app_signature":"0x0000...000","operation_request_json":"{\"permission_id\": 4096}"}'
# Poll: curl http://localhost:8080/api/v1/operations/{operation_id}
```

**Success Criteria:**
- Response includes `logs` field
- Logs accumulate on repeated polling
- No errors in docker-compose logs

---

### ✅ Checkpoint 2: Docker Streaming Implementation
**Files to modify:** `services/agent_runner.py`

**Implementation:**
1. Replace `_execute_container_async()` with streaming version
2. Add `_stream_container_logs()` method
3. Add `_monitor_container_status()` method
4. Use asyncio.gather() to run both in parallel
5. Batch log updates (every 10 lines)

**Key Details:**
- Use `container.logs(stream=True, follow=True)` for streaming
- Run Docker operations in thread pool with `run_in_executor`
- Check for SENTINEL to detect completion
- Handle timeout and container death

**Test Command:**
```bash
make down && make build && make up
# Real agent test (need GEMINI_API_KEY)
curl -X POST http://localhost:8080/api/v1/operations \
  -H "Content-Type: application/json" \
  -d '{"app_signature":"0x0000...000","operation_request_json":"{\"permission_id\": 4096}"}'
# Poll every 2 seconds to see progressive logs
```

**Success Criteria:**
- Logs appear progressively, not all at once
- Container executes properly
- Final result is correct
- No Docker errors

---

### ✅ Checkpoint 3: Memory and Error Handling
**Files to modify:** Already covered in previous checkpoints

**Test Cases:**
1. Quick failure test (invalid operation)
2. Long-running test with lots of output
3. Memory monitoring with `docker stats`

**Success Criteria:**
- Quick failures show logs immediately
- Memory stays stable
- Logs truncate at 10MB limit
- Proper cleanup in all error cases

---

### ✅ Checkpoint 4: SSE Endpoint (Optional)
**Files to modify:** `api/operations.py`, `openapi.yaml`

**Implementation:**
1. Add `/operations/{operation_id}/stream` endpoint
2. Return StreamingResponse with media_type="text/event-stream"
3. Yield events as: `data: {json}\n\n`
4. Poll task store every 0.5s for new logs
5. Close stream when task completes

**Test Command:**
```bash
curl -N http://localhost:8080/api/v1/operations/{operation_id}/stream
# Or in browser console:
# const evtSource = new EventSource('http://localhost:8080/api/v1/operations/{id}/stream');
# evtSource.onmessage = (e) => console.log(JSON.parse(e.data));
```

**Success Criteria:**
- Events stream in real-time
- Connection closes on completion
- No CORS issues

---

### ✅ Checkpoint 5: Full Integration Test
**All files integrated**

**Test Command:**
```bash
make down && make clean && make build && make up
./test_docker_agents.py
# Test both polling and streaming
# Test artifact downloads still work
```

**Success Criteria:**
- All existing functionality works
- No regressions
- Acceptable performance
- Both polling and streaming work

---

## Rollback Strategy

If issues at any checkpoint:
```bash
# Checkpoint 1: git checkout -- services/task_store.py compute/base_agent.py
# Checkpoint 2: git checkout -- services/agent_runner.py
# Checkpoint 3: git checkout -- services/task_store.py services/agent_runner.py
# Checkpoint 4: git checkout -- api/operations.py
# Full rollback: git checkout -- .
```

---

## Critical Implementation Notes

### Thread Safety
- TaskStore operations must be thread-safe
- Use asyncio locks if needed
- Docker operations in thread pool

### Memory Management
- Truncate logs at 10MB
- Keep only last 100-1000 lines in responses
- Future: Stream to S3/R2 for unlimited logs

### Error Cases to Handle
1. Container fails to start
2. Container exits immediately
3. No logs produced
4. Timeout during streaming
5. Docker daemon unavailable
6. Task not found
7. Network interruption (SSE)

### Performance Considerations
- Batch log updates (10 lines)
- 0.5s poll interval for SSE
- Thread pool for Docker ops
- Limit response sizes

---

## Current Implementation Status

### Completed
- [x] Plan created
- [ ] Checkpoint 1: TaskStore modifications
- [ ] Checkpoint 2: Docker streaming
- [ ] Checkpoint 3: Error handling
- [ ] Checkpoint 4: SSE endpoint
- [ ] Checkpoint 5: Integration test

### Next Step
Implement Checkpoint 1: Modify TaskStore for log accumulation

---

## Code Snippets for Quick Reference

### TaskInfo with logs:
```python
@dataclass
class TaskInfo:
    # existing fields...
    logs: List[str] = field(default_factory=list)
    log_size: int = 0
    max_log_size: int = 10_000_000
    truncated: bool = False
```

### Streaming from Docker:
```python
for line in container.logs(stream=True, follow=True):
    decoded = line.decode('utf-8', errors='ignore').rstrip()
    logs.append(decoded)
    if len(logs) % 10 == 0:  # Batch update
        await task_store.append_logs(operation_id, logs[-10:])
```

### SSE format:
```python
yield f"data: {json.dumps({'type': 'log', 'content': line})}\n\n"
```