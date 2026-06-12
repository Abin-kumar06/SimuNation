import React, { useRef, useEffect, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

interface AgentData {
  id: number;
  name: string;
  role: string;
  age: number;
  money: number;
  food: number;
  health: number;
  energy: number;
  happiness: number;
  housing: string;
  x: number;
  y: number;
  is_alive: boolean;
  starving: boolean;
  last_action: string;
  children_count: number;
}

interface MapCanvasProps {
  grid: string[][];
  agents: AgentData[];
  selectedAgentId: number | null;
  onSelectAgent: (agent: AgentData | null) => void;
}

const TILE_COLORS: Record<string, number> = {
  Farm: 0x15803d,     // Green
  Forest: 0x064e3b,   // Dark Green
  River: 0x2563eb,    // Blue
  Village: 0xa16207,  // Brownish gold
  Town: 0x4b5563,     // Grey
  Mine: 0x92400e,     // Bronze/Copper
  Mountain: 0x374151, // Slate Grey
};

const ROLE_COLORS: Record<string, string> = {
  Farmer: "#22c55e",
  Miner: "#f97316",
  Builder: "#a855f7",
  Doctor: "#ec4899",
  Teacher: "#3b82f6",
  Worker: "#f59e0b",
  Trader: "#eab308",
  Merchant: "#06b6d4",
  Child: "#e5e7eb",
};

export const MapCanvas: React.FC<MapCanvasProps> = ({ grid, agents, selectedAgentId, onSelectAgent }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredAgent, setHoveredAgent] = useState<AgentData | null>(null);

  // Keep references to update agent positions dynamically in the anim loop
  const agentsMapRef = useRef<Map<number, { mesh: THREE.Group; data: AgentData }>>(new Map());
  const sceneRef = useRef<THREE.Scene | null>(null);
  const raycasterRef = useRef<THREE.Raycaster>(new THREE.Raycaster());
  const mouseRef = useRef<THREE.Vector2>(new THREE.Vector2());
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);

  const gridWidth = grid[0]?.length || 100;
  const gridHeight = grid.length || 100;
  const halfWidth = gridWidth / 2;
  const halfHeight = gridHeight / 2;

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    // 1. Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b0f19); // Deep dark space background
    scene.fog = new THREE.FogExp2(0x0b0f19, 0.015);
    sceneRef.current = scene;

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 500, 1, 1000);
    camera.position.set(0, 60, 80);
    cameraRef.current = camera;

    // 3. Renderer setup
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setSize(container.clientWidth, 500);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // 4. Orbit Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.05; // Don't go below ground
    controls.minDistance = 10;
    controls.maxDistance = 150;
    controls.target.set(0, 0, 0);

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 0.8);
    sunLight.position.set(40, 80, 30);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 0.5;
    sunLight.shadow.camera.far = 200;
    const d = 60;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    scene.add(sunLight);

    // Subtle grid/sky lighting
    const hemiLight = new THREE.HemisphereLight(0xa5b4fc, 0x1e293b, 0.3);
    scene.add(hemiLight);

    // 6. Build the Grid / Terrain using InstancedMesh for efficiency
    // We group by tile type and create InstancedMeshes
    const tileTypes = ["Farm", "Forest", "River", "Village", "Town", "Mine", "Mountain"];
    const instancedMeshes: Record<string, THREE.InstancedMesh> = {};

    // Standard geometry configurations
    const boxGeo = new THREE.BoxGeometry(0.95, 1, 0.95);

    tileTypes.forEach((type) => {
      // Find count of this tile type
      let count = 0;
      for (let z = 0; z < gridHeight; z++) {
        for (let x = 0; x < gridWidth; x++) {
          if (grid[z][x] === type) count++;
        }
      }
      if (count === 0) return;

      let geom: THREE.BufferGeometry = boxGeo;
      let mat = new THREE.MeshStandardMaterial({
        color: TILE_COLORS[type],
        roughness: 0.8,
        metalness: 0.1,
      });

      if (type === "River") {
        mat.metalness = 0.9;
        mat.roughness = 0.1;
      } else if (type === "Mountain") {
        geom = new THREE.ConeGeometry(0.5, 3.0, 4);
      } else if (type === "Forest") {
        geom = new THREE.ConeGeometry(0.4, 1.2, 5);
      } else if (type === "Village") {
        geom = new THREE.BoxGeometry(0.8, 0.8, 0.8);
      }

      const instMesh = new THREE.InstancedMesh(geom, mat, count);
      instMesh.castShadow = true;
      instMesh.receiveShadow = true;
      scene.add(instMesh);
      instancedMeshes[type] = instMesh;
    });

    // Populate instance matrices
    const tempObj = new THREE.Object3D();
    const typeIndices: Record<string, number> = {};
    tileTypes.forEach(t => typeIndices[t] = 0);

    for (let z = 0; z < gridHeight; z++) {
      for (let x = 0; x < gridWidth; x++) {
        const type = grid[z][x];
        const instMesh = instancedMeshes[type];
        if (!instMesh) continue;

        const idx = typeIndices[type]++;
        const posX = x - halfWidth + 0.5;
        const posZ = z - halfHeight + 0.5;

        tempObj.position.set(posX, 0, posZ);

        if (type === "Mountain") {
          tempObj.position.y = 1.5;
        } else if (type === "Forest") {
          tempObj.position.y = 0.6;
        } else if (type === "Village") {
          tempObj.position.y = 0.4;
        } else if (type === "River") {
          tempObj.position.y = -0.15;
          tempObj.scale.set(1, 0.7, 1);
        } else if (type === "Town") {
          tempObj.scale.set(1, 1.5, 1);
          tempObj.position.y = 0.75;
        } else {
          tempObj.scale.set(1, 0.2, 1);
          tempObj.position.y = 0.1;
        }

        tempObj.updateMatrix();
        instMesh.setMatrixAt(idx, tempObj.matrix);
      }
    }

    // Tell Three.js matrices updated
    Object.values(instancedMeshes).forEach(m => m.instanceMatrix.needsUpdate = true);

    // 7. Render Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();

      // Soft animation / hover effects on agents
      const time = clock.getElapsedTime();
      agentsMapRef.current.forEach(({ mesh, data }) => {
        // Starving agents pulse
        if (data.starving && data.is_alive) {
          const pulse = 1.0 + Math.sin(time * 10) * 0.15;
          mesh.scale.set(pulse, pulse, pulse);
        } else {
          mesh.scale.set(1, 1, 1);
        }

        // Bobbing selected agent
        if (data.id === selectedAgentId) {
          mesh.position.y = 1.2 + Math.sin(time * 5) * 0.25;
        }
      });

      renderer.render(scene, camera);
    };
    animate();

    // Resize Handler
    const handleResize = () => {
      if (!container || !camera || !renderer) return;
      camera.aspect = container.clientWidth / 500;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, 500);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      controls.dispose();
      renderer.dispose();
      // Dispose materials & geometries
      boxGeo.dispose();
      Object.values(instancedMeshes).forEach((m) => {
        m.geometry.dispose();
        if (Array.isArray(m.material)) {
          m.material.forEach((mat) => mat.dispose());
        } else {
          m.material.dispose();
        }
      });
    };
  }, [grid]);

  // Handle Agents creation and updates
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    const currentAgentMap = agentsMapRef.current;
    const incomingAgentIds = new Set(agents.map(a => a.id));

    // Remove dead/missing agents
    currentAgentMap.forEach((val, id) => {
      if (!incomingAgentIds.has(id)) {
        scene.remove(val.mesh);
        // Clean up geometries/materials
        val.mesh.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.geometry.dispose();
            child.material.dispose();
          }
        });
        currentAgentMap.delete(id);
      }
    });

    // Add or update agents
    agents.forEach((agent) => {
      const posX = agent.x - halfWidth + 0.5;
      const posZ = agent.y - halfHeight + 0.5;

      if (currentAgentMap.has(agent.id)) {
        const agentObj = currentAgentMap.get(agent.id)!;
        agentObj.data = agent;

        // Smooth transition/immediate move
        agentObj.mesh.position.x = posX;
        agentObj.mesh.position.z = posZ;
        if (agent.id !== selectedAgentId) {
          agentObj.mesh.position.y = agent.is_alive ? 0.65 : 0.25;
        }

        // Adjust rotation/scale if dead
        const agentBody = agentObj.mesh.getObjectByName("body");
        if (agentBody) {
          if (!agent.is_alive) {
            agentBody.rotation.x = Math.PI / 2; // Lie flat
            (agentBody as THREE.Mesh).material = new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.9 });
          } else {
            agentBody.rotation.x = 0;
          }
        }
      } else {
        // Create new agent mesh representation
        const agentGroup = new THREE.Group();
        agentGroup.position.set(posX, agent.is_alive ? 0.65 : 0.25, posZ);

        // Body geometry
        let bodyGeo: THREE.BufferGeometry = new THREE.SphereGeometry(0.35, 16, 16);
        if (agent.role !== "Child") {
          bodyGeo = new THREE.CapsuleGeometry(0.2, 0.4, 4, 8);
        }

        const bodyMat = new THREE.MeshStandardMaterial({
          color: new THREE.Color(ROLE_COLORS[agent.role] || "#e5e7eb"),
          roughness: 0.5,
          metalness: 0.1
        });

        const bodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
        bodyMesh.name = "body";
        bodyMesh.castShadow = true;
        bodyMesh.userData = { agentId: agent.id }; // Store for raycasting
        agentGroup.add(bodyMesh);

        // If selected agent marker
        if (agent.id === selectedAgentId) {
          const selectionRingGeo = new THREE.RingGeometry(0.5, 0.6, 16);
          selectionRingGeo.rotateX(-Math.PI / 2);
          const selectionRingMat = new THREE.MeshBasicMaterial({ color: 0x6366f1, side: THREE.DoubleSide });
          const ringMesh = new THREE.Mesh(selectionRingGeo, selectionRingMat);
          ringMesh.position.y = -0.3;
          agentGroup.add(ringMesh);
        }

        scene.add(agentGroup);
        currentAgentMap.set(agent.id, { mesh: agentGroup, data: agent });
      }
    });
  }, [agents, selectedAgentId]);

  // Raycast to select agent
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const camera = cameraRef.current;
    const scene = sceneRef.current;
    if (!canvas || !camera || !scene) return;

    const rect = canvas.getBoundingClientRect();
    mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    raycasterRef.current.setFromCamera(mouseRef.current, camera);

    // Get all agent bodies
    const meshesToIntersect: THREE.Object3D[] = [];
    agentsMapRef.current.forEach(({ mesh }) => {
      const body = mesh.getObjectByName("body");
      if (body) meshesToIntersect.push(body);
    });

    const intersects = raycasterRef.current.intersectObjects(meshesToIntersect);

    if (intersects.length > 0) {
      const clickedMesh = intersects[0].object;
      const agentId = clickedMesh.userData.agentId;
      const agentData = agents.find(a => a.id === agentId);
      if (agentData) {
        onSelectAgent(agentData);
      }
    } else {
      onSelectAgent(null);
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const camera = cameraRef.current;
    if (!canvas || !camera) return;

    const rect = canvas.getBoundingClientRect();
    mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    raycasterRef.current.setFromCamera(mouseRef.current, camera);

    const meshesToIntersect: THREE.Object3D[] = [];
    agentsMapRef.current.forEach(({ mesh }) => {
      const body = mesh.getObjectByName("body");
      if (body) meshesToIntersect.push(body);
    });

    const intersects = raycasterRef.current.intersectObjects(meshesToIntersect);
    if (intersects.length > 0) {
      const hoveredMesh = intersects[0].object;
      const agentId = hoveredMesh.userData.agentId;
      const agentData = agents.find(a => a.id === agentId);
      if (agentData) {
        setHoveredAgent(agentData);
        return;
      }
    }
    setHoveredAgent(null);
  };

  return (
    <div ref={containerRef} className="relative border border-slate-700/80 rounded-xl overflow-hidden shadow-2xl bg-slate-950">
      {/* HUD Info */}
      <div className="absolute top-4 right-4 z-10 bg-slate-900/90 border border-slate-700/60 p-3 rounded-lg backdrop-blur-md text-xs text-slate-300 pointer-events-none">
        <h4 className="font-bold text-slate-100 mb-1">Navigation</h4>
        <p>🖱️ Left-Click + Drag: Rotate Village</p>
        <p>🖱️ Right-Click + Drag: Pan Map</p>
        <p>⚙️ Scroll: Zoom In/Out</p>
        <p>👤 Click Agent: Select Details</p>
      </div>

      {hoveredAgent && (
        <div className="absolute top-4 left-4 z-10 bg-slate-900/95 border border-slate-700 p-3 rounded-lg shadow-xl text-xs text-white pointer-events-none min-w-[180px]">
          <div className="font-bold text-indigo-400">{hoveredAgent.name}</div>
          <div className="text-slate-400">{hoveredAgent.role} | Age {hoveredAgent.age}</div>
          <div className="mt-1 flex justify-between">
            <span>Money:</span> <span className="font-semibold text-emerald-400">${hoveredAgent.money}</span>
          </div>
          <div className="flex justify-between">
            <span>Food:</span> <span className="font-semibold text-amber-400">{hoveredAgent.food}</span>
          </div>
          <div className="flex justify-between">
            <span>Happiness:</span> <span className="font-semibold text-sky-400">{hoveredAgent.happiness}%</span>
          </div>
          <div className="text-[10px] text-indigo-300 mt-1 border-t border-slate-700/50 pt-1">
            Status: {hoveredAgent.last_action}
          </div>
        </div>
      )}

      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        onMouseMove={handleCanvasMouseMove}
        className="w-full h-[500px] block cursor-pointer"
      />
    </div>
  );
};
