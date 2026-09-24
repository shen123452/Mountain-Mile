# Third-party notices

This project draws on the MIT-licensed `summer-checkin` project for the agent runtime and tool design, memory and RAG logic, and voxel terrain mathematics. Adapted files will be listed here when those milestones are implemented.

The following M2 files adapt the reference terrain mathematics and island construction ideas into framework-independent TypeScript and Three.js for Mountain Mile:

- `frontend/src/components/three/terrain.ts`
- `frontend/src/components/three/scene.ts`
- `frontend/src/components/three/decorations.ts`

The following M4 files adapt the reference agent runtime and tool catalog concepts to Python, FastAPI, and the OpenAI SDK:

- `backend/app/agent/orchestrator.py`
- `backend/app/tools/registry.py`

## summer-checkin license

MIT License

Copyright (c) 2026 ruan-weibo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
