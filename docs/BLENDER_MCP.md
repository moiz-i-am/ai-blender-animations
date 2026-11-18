# Blender MCP (optional, interactive)

**What it's for:** Claude controls a *live* Blender window. It can look at the scene, move things, take viewport screenshots, and try layouts quickly.
**What it's not for:** the repeatable pipeline. Final scenes always live as Python in `blender/scenes/*.py` and render headless with `make_episode.py`, so the PC and the Mac get identical results.

A typical loop:
1. Run `py make_episode.py blend traffic_camera`. This writes `output/traffic_camera/scene.blend`.
2. Open that file in Blender and start the MCP connection (see below).
3. Ask Claude, for example: "look at the viewport from the reveal_pole camera; the radar label is too close, move the camera back and give me the new pos/target values".
4. Claude writes the result back into the episode JSON or the scene module.

## Setup (community `blender-mcp` server)

These steps use the popular open-source server at <https://github.com/ahujasid/blender-mcp>. MCP tooling changes quickly, so if anything differs, **follow that repo's README.** If your Claude app offers an official Blender connector, you can use that instead.

1. **Install uv.** On Windows: `winget install -e --id astral-sh.uv`. On macOS: `brew install uv`.
2. **Install the Blender add-on.** Download `addon.py` from the repo. In Blender, go to *Edit → Preferences → Add-ons*, then use the ▾ menu → *Install from Disk…* and pick `addon.py`. Enable "Interface: Blender MCP".
3. **Start the connection.** In the 3D viewport press `N`, open the **BlenderMCP** tab, and click **Connect / Start server**. You do this each Blender session.
4. **Connect Claude Code.** This repo already includes `.mcp.json`:
   ```json
   { "mcpServers": { "blender": { "command": "uvx", "args": ["blender-mcp"] } } }
   ```
   Start `claude` in the repo folder and approve the `blender` server when it asks. Run `/mcp` to check that it's connected.
   *Windows:* if the server fails to start, change the command to `"cmd"` with args `["/c", "uvx", "blender-mcp"]`.
5. **Or connect Claude Desktop (chat).** Open *Settings → Developer → Edit Config* and add the same `mcpServers` block, then restart the app.

## Notes
- Only one client (Claude Code *or* Claude Desktop) should be connected to Blender at a time.
- The add-on lets Claude run arbitrary Python inside Blender, so save your work first.
- The server can optionally download Poly Haven or Sketchfab assets. Check licences, and record them in `assets/models/README.md`.
