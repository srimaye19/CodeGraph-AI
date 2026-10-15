/**
 * CodeGraph AI - Interactive Graph Visualizer
 * Integrates vis-network for physics simulation, zooming, node filtering, and property inspection.
 */

const GraphVisualizer = {
  network: null,
  container: null,
  nodesDataset: null,
  edgesDataset: null,
  allNodes: [],
  allEdges: [],
  physicsEnabled: true,

  init(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) return;

    this.nodesDataset = new vis.DataSet([]);
    this.edgesDataset = new vis.DataSet([]);

    const options = {
      nodes: {
        font: {
          color: "#f0f6fc",
          size: 13,
          face: "Inter, sans-serif"
        },
        borderWidth: 1.5,
        shadow: {
          enabled: true,
          color: "rgba(0,0,0,0.5)",
          size: 6
        }
      },
      edges: {
        width: 1.2,
        color: {
          color: "#484f58",
          highlight: "#58a6ff",
          hover: "#8b949e"
        },
        font: {
          color: "#8b949e",
          size: 10,
          align: "middle"
        },
        arrows: {
          to: { enabled: true, scaleFactor: 0.7 }
        },
        smooth: {
          type: "continuous"
        }
      },
      physics: {
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -35,
          centralGravity: 0.005,
          springLength: 85,
          springConstant: 0.18
        },
        stabilization: { iterations: 120 }
      },
      interaction: {
        hover: true,
        tooltipDelay: 150,
        zoomView: true,
        dragView: true
      }
    };

    this.network = new vis.Network(
      this.container,
      { nodes: this.nodesDataset, edges: this.edgesDataset },
      options
    );

    // Event listeners
    this.network.on("click", (params) => this.handleNodeClick(params));
  },

  setData(nodes, edges) {
    this.allNodes = nodes || [];
    this.allEdges = edges || [];
    this.applyFilters();
  },

  applyFilters() {
    if (!this.nodesDataset || !this.edgesDataset) return;

    // Read active checkboxes
    const activeTypes = new Set();
    if (document.getElementById("filter-files")?.checked) activeTypes.add("file");
    if (document.getElementById("filter-symbols")?.checked) activeTypes.add("symbol");
    if (document.getElementById("filter-packages")?.checked) activeTypes.add("package");
    if (document.getElementById("filter-findings")?.checked) activeTypes.add("finding");

    const filteredNodes = this.allNodes.filter(n => activeTypes.has(n.type));
    const activeNodeIds = new Set(filteredNodes.map(n => n.id));

    const filteredEdges = this.allEdges.filter(
      e => activeNodeIds.has(e.from) && activeNodeIds.has(e.to)
    );

    this.nodesDataset.clear();
    this.edgesDataset.clear();

    this.nodesDataset.add(filteredNodes);
    this.edgesDataset.add(filteredEdges);

    const countElem = document.getElementById("graph-node-count");
    if (countElem) {
      countElem.textContent = `${filteredNodes.length} nodes, ${filteredEdges.length} edges`;
    }
  },

  handleNodeClick(params) {
    const inspector = document.getElementById("graph-inspector");
    if (!inspector) return;

    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      const node = this.allNodes.find(n => n.id === nodeId);
      if (node) {
        this.renderInspector(node);
      }
    } else {
      inspector.innerHTML = `
        <div class="inspector-title">Node Inspector</div>
        <p style="font-size: 13px; color: var(--text-muted);">
          Click any file, symbol, package, or finding node in the graph to inspect its properties and relationships.
        </p>
      `;
    }
  },

  renderInspector(node) {
    const inspector = document.getElementById("graph-inspector");
    let typeBadgeColor = "#58a6ff";
    if (node.type === "symbol") typeBadgeColor = "#3fb950";
    if (node.type === "package") typeBadgeColor = "#bc8cff";
    if (node.type === "finding") typeBadgeColor = "#f85149";

    let html = `
      <div class="inspector-title" style="display: flex; justify-content: space-between; align-items: center;">
        <span>${this.escapeHtml(node.label)}</span>
        <span class="sev-pill" style="background-color: rgba(255,255,255,0.1); color: ${typeBadgeColor}; border-color: ${typeBadgeColor};">
          ${node.type.toUpperCase()}
        </span>
      </div>
      <div class="inspector-prop">
        <span class="prop-name">ID</span>
        <span class="prop-value" style="font-size: 11px;">${this.escapeHtml(node.id)}</span>
      </div>
    `;

    if (node.properties) {
      for (const [key, val] of Object.entries(node.properties)) {
        html += `
          <div class="inspector-prop">
            <span class="prop-name">${this.escapeHtml(key)}</span>
            <span class="prop-value">${this.escapeHtml(String(val))}</span>
          </div>
        `;
      }
    }

    inspector.innerHTML = html;
  },

  focusNode(query) {
    if (!query || !this.network) return;
    const q = query.toLowerCase();
    const matched = this.allNodes.find(
      n => n.label.toLowerCase().includes(q) || (n.properties?.path && n.properties.path.toLowerCase().includes(q))
    );

    if (matched) {
      this.network.focus(matched.id, {
        scale: 1.4,
        animation: { duration: 600, easingFunction: "easeInOutQuad" }
      });
      this.network.selectNodes([matched.id]);
      this.renderInspector(matched);
    }
  },

  togglePhysics() {
    this.physicsEnabled = !this.physicsEnabled;
    if (this.network) {
      this.network.setOptions({ physics: { enabled: this.physicsEnabled } });
    }
    return this.physicsEnabled;
  },

  fit() {
    if (this.network) {
      this.network.fit({ animation: { duration: 500 } });
    }
  },

  escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
};
