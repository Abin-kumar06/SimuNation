import React, { useRef, useEffect, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { MTLLoader } from "three/examples/jsm/loaders/MTLLoader.js";
import { TGALoader } from "three/examples/jsm/loaders/TGALoader.js";

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

interface MapCanvas3DProps {
  grid: string[][];
  agents: AgentData[];
  selectedAgentId: number | null;
  onSelectAgent: (agent: AgentData | null) => void;
}

const TILE_COLORS: Record<string, string> = {
  Farm: "#2e7d32",
  Forest: "#1b5e20",
  River: "#0288d1",
  Village: "#f57f17",
  Town: "#616161",
  Mine: "#8d6e63",
  Mountain: "#424242",
};

const ROLE_COLORS: Record<string, string> = {
  Farmer: "#4caf50",
  Miner: "#ff9800",
  Builder: "#9c27b0",
  Doctor: "#e91e63",
  Teacher: "#2196f3",
  Worker: "#ffc107",
  Trader: "#ffeb3b",
  Merchant: "#00bcd4",
  Child: "#cfd8dc",
};

export const MapCanvas3D: React.FC<MapCanvas3DProps> = ({
  grid,
  agents,
  selectedAgentId,
  onSelectAgent,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Overlay refs for mapping 3D positions to 2D html tags
  const overlayRef = useRef<HTMLDivElement>(null);

  // States
  const [loadProgress, setLoadProgress] = useState<number>(0);
  const [loadingStatus, setLoadingStatus] = useState<string>("Initializing Scene...");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [hoveredAgent, setHoveredAgent] = useState<AgentData | null>(null);

  // Three.js object references
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  
  // Track agent meshes to update position and raycast
  const agentMeshes = useRef<Record<number, THREE.Group>>({});
  
  // Grid size
  const gridWidth = grid[0]?.length || 100;
  const gridHeight = grid.length || 100;

  // Track resizing, cleanups
  useEffect(() => {
    if (!canvasRef.current || !containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = 500;

    // 1. Scene Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#090d16");
    scene.fog = new THREE.FogExp2("#090d16", 0.012);
    sceneRef.current = scene;

    // 2. Camera Setup
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    // Position angle view over the whole grid
    camera.position.set(0, 50, 65);
    cameraRef.current = camera;

    // 3. Renderer Setup
    const renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.current,
      antialias: true,
      alpha: false,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    rendererRef.current = renderer;

    // 4. Orbit Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2.1; // Don't allow camera to go below ground
    controls.minDistance = 5;
    controls.maxDistance = 150;
    controls.target.set(0, 0, 0);
    controlsRef.current = controls;

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight("#4f5b73", 0.6);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight("#8fa3ff", "#2c3459", 0.4);
    hemiLight.position.set(0, 100, 0);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight("#fff6e6", 0.9);
    sunLight.position.set(30, 80, 40);
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
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);

    // 6. Terrain Generation using single InstancedMesh for extreme performance
    setLoadingStatus("Generating terrain grid...");
    
    // Compute total mountains and forests to allocate tree instances
    let forestCount = 0;
    for (let y = 0; y < gridHeight; y++) {
      for (let x = 0; x < gridWidth; x++) {
        if (grid[y][x] === "Forest") forestCount++;
      }
    }

    const groundGeom = new THREE.BoxGeometry(0.95, 1, 0.95);
    const groundMat = new THREE.MeshStandardMaterial({
      roughness: 0.8,
      metalness: 0.1,
    });
    const groundInstanced = new THREE.InstancedMesh(
      groundGeom,
      groundMat,
      gridWidth * gridHeight
    );
    groundInstanced.receiveShadow = true;
    groundInstanced.castShadow = true;

    const dummy = new THREE.Object3D();
    let idx = 0;

    for (let y = 0; y < gridHeight; y++) {
      for (let x = 0; x < gridWidth; x++) {
        const type = grid[y][x];
        const color = new THREE.Color(TILE_COLORS[type] || "#1e293b");

        // Scale and raise blocks based on geographical types
        dummy.position.set(x - gridWidth / 2, 0, y - gridHeight / 2);
        dummy.scale.set(1, 1, 1);

        if (type === "Mountain") {
          const height = 3 + Math.sin(x * 0.3) * Math.cos(y * 0.3) * 3 + Math.random() * 2;
          dummy.position.y = height / 2 - 0.5;
          dummy.scale.y = height;
        } else if (type === "River") {
          dummy.position.y = -0.35;
          dummy.scale.y = 0.3;
        } else if (type === "Mine") {
          dummy.position.y = 0.4;
          dummy.scale.y = 1.8;
        } else if (type === "Village" || type === "Town") {
          dummy.position.y = -0.1;
          dummy.scale.y = 0.8;
        } else {
          // Farm / Plain
          dummy.position.y = -0.4;
          dummy.scale.y = 0.2;
        }

        dummy.updateMatrix();
        groundInstanced.setMatrixAt(idx, dummy.matrix);
        groundInstanced.setColorAt(idx, color);
        idx++;
      }
    }
    scene.add(groundInstanced);

    // 7. Procedural pine trees in forest tiles
    if (forestCount > 0) {
      setLoadingStatus("Planting voxel forest...");
      
      const trunkGeom = new THREE.CylinderGeometry(0.08, 0.12, 0.6, 5);
      const trunkMat = new THREE.MeshStandardMaterial({ color: "#5d4037", roughness: 0.9 });
      const trunkInstanced = new THREE.InstancedMesh(trunkGeom, trunkMat, forestCount);
      trunkInstanced.castShadow = true;
      
      const leavesGeom = new THREE.ConeGeometry(0.35, 1.2, 5);
      const leavesMat = new THREE.MeshStandardMaterial({ color: "#0a3c10", roughness: 0.9 });
      const leavesInstanced = new THREE.InstancedMesh(leavesGeom, leavesMat, forestCount);
      leavesInstanced.castShadow = true;

      let forestIdx = 0;
      for (let y = 0; y < gridHeight; y++) {
        for (let x = 0; x < gridWidth; x++) {
          if (grid[y][x] === "Forest") {
            const px = x - gridWidth / 2 + (Math.random() - 0.5) * 0.3;
            const pz = y - gridHeight / 2 + (Math.random() - 0.5) * 0.3;
            
            // Trunk matrix
            dummy.position.set(px, 0.3 - 0.4, pz);
            dummy.scale.set(1, 1, 1);
            dummy.updateMatrix();
            trunkInstanced.setMatrixAt(forestIdx, dummy.matrix);

            // Leaves matrix
            dummy.position.set(px, 0.9 - 0.4, pz);
            dummy.scale.set(1, 1, 1);
            dummy.updateMatrix();
            leavesInstanced.setMatrixAt(forestIdx, dummy.matrix);

            forestIdx++;
          }
        }
      }
      scene.add(trunkInstanced);
      scene.add(leavesInstanced);
    }

    // 8. Load 3D Street Model (OBJ/MTL)
    setLoadingStatus("Loading 3D town model...");
    const manager = new THREE.LoadingManager();
    manager.addHandler(/\.tga$/i, new TGALoader());
    
    manager.onProgress = (_, itemsLoaded, itemsTotal) => {
      const prog = Math.round((itemsLoaded / itemsTotal) * 100);
      setLoadProgress(prog);
    };

    const mtlLoader = new MTLLoader(manager);
    mtlLoader.setPath("/models/");
    mtlLoader.load(
      "Street_environment_V01.mtl",
      (materials) => {
        materials.preload();
        
        const objLoader = new OBJLoader(manager);
        objLoader.setMaterials(materials);
        objLoader.setPath("/models/");
        objLoader.load(
          "Street_environment_V01.obj",
          (object) => {
            // Apply scales and shadows
            object.traverse((child) => {
              if (child instanceof THREE.Mesh) {
                child.castShadow = true;
                child.receiveShadow = true;
              }
            });

            // Adjust model scale: normal exported sizes can vary, 0.08 seems like a great grid fit
            object.scale.set(0.065, 0.065, 0.065);

            // Simulation has Town / Village structures at centers:
            // Town 1: (30, 30) -> (-20, -20)
            const town1 = object.clone();
            town1.position.set(-20, 0, -20);
            town1.rotation.y = Math.PI / 4;
            scene.add(town1);

            // Town 2: (70, 75) -> (20, 25)
            const town2 = object.clone();
            town2.position.set(20, 0, 25);
            town2.rotation.y = -Math.PI / 2.5;
            scene.add(town2);

            // Village 1: (45, 50) -> (-5, 0)
            const village1 = object.clone();
            village1.scale.set(0.045, 0.045, 0.045);
            village1.position.set(-5, 0, 0);
            village1.rotation.y = Math.PI / 2;
            scene.add(village1);

            // Village 2: (20, 75) -> (-30, 25)
            const village2 = object.clone();
            village2.scale.set(0.045, 0.045, 0.045);
            village2.position.set(-30, 0, 25);
            scene.add(village2);

            // Village 3: (80, 25) -> (30, -25)
            const village3 = object.clone();
            village3.scale.set(0.045, 0.045, 0.045);
            village3.position.set(30, 0, -25);
            village3.rotation.y = -Math.PI;
            scene.add(village3);

            setIsLoading(false);
          },
          undefined,
          (err) => {
            console.error("Failed loading OBJ:", err);
            // Fallback so interface still displays if model has glitches
            setIsLoading(false);
          }
        );
      },
      undefined,
      (err) => {
        console.error("Failed loading MTL:", err);
        setIsLoading(false);
      }
    );

    // 9. Resize handler
    const handleResize = () => {
      if (!containerRef.current || !rendererRef.current || !cameraRef.current) return;
      const w = containerRef.current.clientWidth;
      cameraRef.current.aspect = w / height;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, height);
    };
    window.addEventListener("resize", handleResize);

    // 10. Frame/Animation Loop
    let animationFrameId: number;
    
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      // Update Controls
      if (controlsRef.current) {
        controlsRef.current.update();
      }

      // Render Scene
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
    };
    animate();

    // Clean up
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      if (rendererRef.current) {
        rendererRef.current.dispose();
      }
      groundGeom.dispose();
      groundMat.dispose();
    };
  }, [gridWidth, gridHeight]);

  // Handle Agents Creation, Interpolation, and Selection update
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    // 1. Remove meshes of deceased or removed agents
    const currentAgentIds = new Set(agents.map(a => a.id));
    Object.keys(agentMeshes.current).forEach((idStr) => {
      const id = parseInt(idStr);
      if (!currentAgentIds.has(id)) {
        scene.remove(agentMeshes.current[id]);
        delete agentMeshes.current[id];
      }
    });

    // 2. Add or update active agents
    agents.forEach((agent) => {
      let group = agentMeshes.current[agent.id];

      // If dead, render differently or remove
      if (!agent.is_alive) {
        if (group) {
          scene.remove(group);
          delete agentMeshes.current[agent.id];
        }
        return; // skip dead agents in 3D scene (or can represent with tombstones)
      }

      if (!group) {
        // Create new stylized agent marker (Peg shape)
        group = new THREE.Group();
        group.userData = { agentId: agent.id };

        // Body: Cone or cylinder
        const bodyGeom = new THREE.CylinderGeometry(0.12, 0.28, 0.8, 8);
        const bodyMat = new THREE.MeshStandardMaterial({
          color: new THREE.Color(ROLE_COLORS[agent.role] || "#e5e7eb"),
          roughness: 0.5,
          metalness: 0.1,
        });
        const body = new THREE.Mesh(bodyGeom, bodyMat);
        body.position.y = 0.4;
        body.castShadow = true;
        group.add(body);

        // Head: Sphere
        const headGeom = new THREE.SphereGeometry(0.2, 8, 8);
        const headMat = new THREE.MeshStandardMaterial({
          color: new THREE.Color(ROLE_COLORS[agent.role] || "#e5e7eb"),
          roughness: 0.3,
        });
        const head = new THREE.Mesh(headGeom, headMat);
        head.position.y = 0.9;
        head.castShadow = true;
        group.add(head);

        // Selected indicator ring
        const ringGeom = new THREE.RingGeometry(0.42, 0.52, 16);
        ringGeom.rotateX(-Math.PI / 2);
        const ringMat = new THREE.MeshBasicMaterial({
          color: 0x6366f1,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.8,
        });
        const selectionRing = new THREE.Mesh(ringGeom, ringMat);
        selectionRing.name = "selectionRing";
        selectionRing.position.y = 0.01;
        selectionRing.visible = false;
        group.add(selectionRing);

        // Starving alert ring
        const starvRingGeom = new THREE.RingGeometry(0.32, 0.38, 16);
        starvRingGeom.rotateX(-Math.PI / 2);
        const starvRingMat = new THREE.MeshBasicMaterial({
          color: 0xf97316,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.95,
        });
        const starvingRing = new THREE.Mesh(starvRingGeom, starvRingMat);
        starvingRing.name = "starvingRing";
        starvingRing.position.y = 0.03;
        starvingRing.visible = agent.starving;
        group.add(starvingRing);

        // Set initial position immediately
        const initX = agent.x - gridWidth / 2;
        const initZ = agent.y - gridHeight / 2;
        const initY = getTileHeight(agent.x, agent.y);
        group.position.set(initX, initY, initZ);

        scene.add(group);
        agentMeshes.current[agent.id] = group;
      }
    });
  }, [agents, gridWidth, gridHeight]);

  // Helper: calculate tile height
  const getTileHeight = (x: number, y: number): number => {
    const type = grid[y]?.[x] || "Farm";
    if (type === "Mountain") return 1.5;
    if (type === "River") return -0.25;
    if (type === "Mine") return 0.4;
    return -0.3; // Flat lands
  };

  // Position interpolation frame loop
  useEffect(() => {
    let active = true;
    const lerpFactor = 0.085; // Agent glide speed

    const updatePositions = () => {
      if (!active) return;

      agents.forEach((agent) => {
        const mesh = agentMeshes.current[agent.id];
        if (mesh) {
          const targetX = agent.x - gridWidth / 2;
          const targetZ = agent.y - gridHeight / 2;
          const targetY = getTileHeight(agent.x, agent.y);

          // Lerp position values
          mesh.position.x += (targetX - mesh.position.x) * lerpFactor;
          mesh.position.z += (targetZ - mesh.position.z) * lerpFactor;
          mesh.position.y += (targetY - mesh.position.y) * lerpFactor;

          // Animate selection indicator
          const selRing = mesh.getObjectByName("selectionRing");
          if (selRing) {
            selRing.visible = agent.id === selectedAgentId;
            if (selRing.visible) {
              selRing.rotation.y += 0.03;
            }
          }

          // Animate starvation indicator
          const starvRing = mesh.getObjectByName("starvingRing");
          if (starvRing) {
            starvRing.visible = agent.starving;
            if (starvRing.visible) {
              const pulse = 1.0 + 0.15 * Math.sin(Date.now() * 0.006);
              starvRing.scale.set(pulse, pulse, pulse);
            }
          }
        }
      });

      // Project tags coordinates to 2D HTML overlays
      updateOverlayHTMLTags();

      requestAnimationFrame(updatePositions);
    };

    updatePositions();

    return () => {
      active = false;
    };
  }, [agents, selectedAgentId]);

  // Project agent coordinates to 2D Screen Overlay divs
  const updateOverlayHTMLTags = () => {
    const camera = cameraRef.current;
    const renderer = rendererRef.current;
    if (!camera || !renderer || !overlayRef.current) return;

    const width = renderer.domElement.clientWidth;
    const height = renderer.domElement.clientHeight;

    const tempV = new THREE.Vector3();

    agents.forEach((agent) => {
      const mesh = agentMeshes.current[agent.id];
      const el = document.getElementById(`agent-tag-${agent.id}`);
      if (!mesh || !el) return;

      mesh.getWorldPosition(tempV);
      tempV.y += 1.35; // Head top offset

      tempV.project(camera);

      // Check if behind screen camera depth bounds
      const isBehindCamera = tempV.z > 1;

      if (isBehindCamera) {
        el.style.display = "none";
      } else {
        const x = (tempV.x * 0.5 + 0.5) * width;
        const y = (-tempV.y * 0.5 + 0.5) * height;

        // Clip/Hide if off-screen boundary
        if (x < 0 || x > width || y < 0 || y > height) {
          el.style.display = "none";
        } else {
          el.style.display = "block";
          el.style.transform = `translate(-50%, -100%) translate(${x}px, ${y}px)`;
        }
      }
    });
  };

  // Click Raycaster Handler
  const [clickStart, setClickStart] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setClickStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const moveDist = Math.hypot(e.clientX - clickStart.x, e.clientY - clickStart.y);
    if (moveDist > 5) return; // Disregard clicks during camera panning

    const camera = cameraRef.current;
    if (!camera || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);

    // Intersect groups
    const intersects = raycaster.intersectObjects(
      Object.values(agentMeshes.current),
      true
    );

    if (intersects.length > 0) {
      let obj: THREE.Object3D | null = intersects[0].object;
      while (obj && obj.userData?.agentId === undefined) {
        obj = obj.parent;
      }
      if (obj && obj.userData?.agentId !== undefined) {
        const agent = agents.find((a) => a.id === obj!.userData.agentId);
        if (agent) {
          onSelectAgent(agent);
          return;
        }
      }
    }
    // Deselect if clicking empty land
    onSelectAgent(null);
  };

  // Hover detection handler
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const camera = cameraRef.current;
    if (!camera || !canvasRef.current || isLoading) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(
      Object.values(agentMeshes.current),
      true
    );

    if (intersects.length > 0) {
      let obj: THREE.Object3D | null = intersects[0].object;
      while (obj && obj.userData?.agentId === undefined) {
        obj = obj.parent;
      }
      if (obj && obj.userData?.agentId !== undefined) {
        const agent = agents.find((a) => a.id === obj!.userData.agentId);
        if (agent) {
          setHoveredAgent(agent);
          canvasRef.current.style.cursor = "pointer";
          return;
        }
      }
    }
    setHoveredAgent(null);
    canvasRef.current.style.cursor = "grab";
  };

  return (
    <div
      ref={containerRef}
      className="relative border border-slate-700/80 rounded-xl overflow-hidden shadow-2xl bg-slate-950 select-none"
    >
      {/* 3D WebGL Canvas */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseMove={handleMouseMove}
        className="w-full h-[500px] cursor-grab active:cursor-grabbing block"
      />

      {/* 2D Projection Tags Container overlay */}
      <div
        ref={overlayRef}
        className="absolute inset-0 pointer-events-none overflow-hidden"
      >
        {agents.map((agent) => {
          if (!agent.is_alive) return null;
          
          const isSelected = agent.id === selectedAgentId;
          const isHovered = agent.id === hoveredAgent?.id;
          
          // Only show label if selected, hovered, or starving to avoid massive clutter
          if (!isSelected && !isHovered && !agent.starving) return null;

          let badgeColor = "bg-indigo-600 border-indigo-400";
          if (agent.starving) badgeColor = "bg-amber-600 border-amber-400 animate-pulse";
          if (isHovered && !isSelected && !agent.starving) badgeColor = "bg-slate-800 border-slate-600";

          return (
            <div
              key={agent.id}
              id={`agent-tag-${agent.id}`}
              className="absolute left-0 top-0 transition-opacity duration-150"
              style={{ display: "none" }}
            >
              <div
                className={`px-2 py-0.5 rounded border text-[10px] font-bold text-white shadow-lg flex items-center gap-1 ${badgeColor}`}
              >
                <span>{agent.name}</span>
                <span className="opacity-75">({agent.role})</span>
                {agent.starving && <span className="text-amber-200 block">⚠️ starving</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-sm flex flex-col items-center justify-center gap-4 text-center p-6 z-20">
          <div className="w-12 h-12 rounded-full border-4 border-indigo-600/30 border-t-indigo-500 animate-spin" />
          <div className="flex flex-col gap-1">
            <h4 className="font-semibold text-slate-100">{loadingStatus}</h4>
            <span className="text-xs text-slate-400">
              {loadProgress > 0 ? `Loading assets: ${loadProgress}%` : "Setting up camera & lights..."}
            </span>
          </div>
        </div>
      )}

      {/* Instructions Controls overlay */}
      <div className="absolute bottom-4 right-4 bg-slate-900/85 backdrop-blur border border-slate-800 text-[10px] text-slate-400 p-2.5 rounded-lg flex flex-col gap-1 pointer-events-none">
        <span className="font-semibold text-slate-200 uppercase tracking-wider mb-0.5">3D Camera Controls</span>
        <div>🖱️ Left click + Drag to rotate view</div>
        <div>🖱️ Right click + Drag to pan map</div>
        <div>🌀 Scroll wheel to zoom in/out</div>
        <div>👆 Click agents to inspect stats</div>
      </div>
    </div>
  );
};
