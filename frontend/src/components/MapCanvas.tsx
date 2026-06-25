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
  Farm: 0x3f6212,     // Rich field green/brown
  Forest: 0x064e3b,   // Deep pine green
  River: 0x0284c7,    // Sky blue water
  Village: 0x78350f,  // Warm clay/wood brown
  Town: 0x334155,     // Slate grey
  Mine: 0x451a03,     // Deep earth brown
  Mountain: 0x475569, // Rocky grey
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

  // Keep references to animate agents smoothly
  const agentsMapRef = useRef<Map<number, {
    group: THREE.Group;
    data: AgentData;
    visualPos: THREE.Vector3;
    leftLeg: THREE.Object3D;
    rightLeg: THREE.Object3D;
    leftArm: THREE.Object3D;
    rightArm: THREE.Object3D;
    body: THREE.Object3D;
  }>>(new Map());

  const sceneRef = useRef<THREE.Scene | null>(null);
  const raycasterRef = useRef<THREE.Raycaster>(new THREE.Raycaster());
  const mouseRef = useRef<THREE.Vector2>(new THREE.Vector2());
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const riverMaterialRef = useRef<THREE.MeshStandardMaterial | null>(null);

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
    scene.background = new THREE.Color(0x0f172a); // Deep dark space background
    scene.fog = new THREE.FogExp2(0x0f172a, 0.012);
    sceneRef.current = scene;

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 500, 1, 1000);
    camera.position.set(0, 45, 60);
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
    controls.maxPolarAngle = Math.PI / 2 - 0.05; // Prevent camera from going underground
    controls.minDistance = 5;
    controls.maxDistance = 140;
    controls.target.set(0, 0, 0);

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.35);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfef08a, 0.95); // Warm sun
    sunLight.position.set(50, 75, 40);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 0.5;
    sunLight.shadow.camera.far = 180;
    const d = 55;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    scene.add(sunLight);

    const hemiLight = new THREE.HemisphereLight(0xbfdbfe, 0x1e293b, 0.45); // Sky/ground gradient
    scene.add(hemiLight);

    // 6. Build Satellite Terrain using InstancedMeshes
    const tileTypes = ["Farm", "Forest", "River", "Village", "Town", "Mine", "Mountain"];
    const baseInstancedMeshes: Record<string, THREE.InstancedMesh> = {};
    const detailInstancedMeshes: Record<string, THREE.InstancedMesh[]> = {};

    // Base geometry for ground tile block
    const baseGeo = new THREE.BoxGeometry(0.98, 0.2, 0.98);

    // Count tiles to dimension InstancedMeshes
    const tileCounts: Record<string, number> = {};
    tileTypes.forEach(t => tileCounts[t] = 0);
    for (let z = 0; z < gridHeight; z++) {
      for (let x = 0; x < gridWidth; x++) {
        const type = grid[z][x];
        tileCounts[type] = (tileCounts[type] || 0) + 1;
      }
    }

    // River material reference to animate it
    const riverMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7,
      roughness: 0.1,
      metalness: 0.8,
      flatShading: true,
    });
    riverMaterialRef.current = riverMat;

    // Initialize Instanced Meshes for Bases
    tileTypes.forEach((type) => {
      const count = tileCounts[type];
      if (count === 0) return;

      const baseMat = new THREE.MeshStandardMaterial({
        color: TILE_COLORS[type],
        roughness: 0.85,
        metalness: 0.05,
      });

      const baseMesh = new THREE.InstancedMesh(baseGeo, type === "River" ? riverMat : baseMat, count);
      baseMesh.receiveShadow = true;
      scene.add(baseMesh);
      baseInstancedMeshes[type] = baseMesh;

      // Initialize secondary InstancedMeshes for detailed satellite items
      detailInstancedMeshes[type] = [];

      if (type === "Forest") {
        // Pine trees: trunk + foliage
        // We will place 2 trees per forest tile, so count * 2
        const trunkGeo = new THREE.CylinderGeometry(0.04, 0.06, 0.3, 5);
        const trunkMat = new THREE.MeshStandardMaterial({ color: 0x5c4033, roughness: 0.9 });
        const leafGeo = new THREE.ConeGeometry(0.25, 0.7, 5);
        const leafMat = new THREE.MeshStandardMaterial({ color: 0x064e3b, roughness: 0.8 });

        const trunkMesh = new THREE.InstancedMesh(trunkGeo, trunkMat, count * 2);
        const leafMesh = new THREE.InstancedMesh(leafGeo, leafMat, count * 2);
        trunkMesh.castShadow = true;
        leafMesh.castShadow = true;

        scene.add(trunkMesh, leafMesh);
        detailInstancedMeshes[type].push(trunkMesh, leafMesh);

      } else if (type === "Village") {
        // Detailed cottages: Base house + red gabled roof
        const houseGeo = new THREE.BoxGeometry(0.5, 0.4, 0.5);
        const houseMat = new THREE.MeshStandardMaterial({ color: 0xf3f4f6, roughness: 0.7 }); // plaster white
        const roofGeo = new THREE.ConeGeometry(0.42, 0.35, 4);
        const roofMat = new THREE.MeshStandardMaterial({ color: 0x991b1b, roughness: 0.6 }); // red brick roof

        const houseMesh = new THREE.InstancedMesh(houseGeo, houseMat, count);
        const roofMesh = new THREE.InstancedMesh(roofGeo, roofMat, count);
        houseMesh.castShadow = true;
        roofMesh.castShadow = true;

        scene.add(houseMesh, roofMesh);
        detailInstancedMeshes[type].push(houseMesh, roofMesh);

      } else if (type === "Town") {
        // Satellite skyscrapers with window structures
        const buildGeo = new THREE.BoxGeometry(0.6, 1.2, 0.6);
        const buildMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.2, roughness: 0.3 });

        const buildMesh = new THREE.InstancedMesh(buildGeo, buildMat, count);
        buildMesh.castShadow = true;
        scene.add(buildMesh);
        detailInstancedMeshes[type].push(buildMesh);

      } else if (type === "Mountain") {
        // Rocky peak cone + white snow-capped peak cone
        const rockyGeo = new THREE.ConeGeometry(0.48, 2.2, 4);
        const rockyMat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.9 });
        const snowGeo = new THREE.ConeGeometry(0.25, 0.7, 4);
        const snowMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.8 });

        const rockyMesh = new THREE.InstancedMesh(rockyGeo, rockyMat, count);
        const snowMesh = new THREE.InstancedMesh(snowGeo, snowMat, count);
        rockyMesh.castShadow = true;
        snowMesh.castShadow = true;

        scene.add(rockyMesh, snowMesh);
        detailInstancedMeshes[type].push(rockyMesh, snowMesh);

      } else if (type === "Farm") {
        // Striped crop lines
        const cropGeo = new THREE.BoxGeometry(0.85, 0.05, 0.08);
        const cropMat = new THREE.MeshStandardMaterial({ color: 0x84cc16, roughness: 0.9 }); // Light crop green
        // 3 rows of crops per farm tile
        const cropMesh = new THREE.InstancedMesh(cropGeo, cropMat, count * 3);
        cropMesh.castShadow = true;
        scene.add(cropMesh);
        detailInstancedMeshes[type].push(cropMesh);

      } else if (type === "Mine") {
        // Simple mining shaft framing / scaffolds
        const postGeo = new THREE.BoxGeometry(0.1, 0.5, 0.1);
        const postMat = new THREE.MeshStandardMaterial({ color: 0x27272a, roughness: 0.9 });
        const beamMesh = new THREE.InstancedMesh(postGeo, postMat, count * 3); // 2 posts + 1 beam
        beamMesh.castShadow = true;
        scene.add(beamMesh);
        detailInstancedMeshes[type].push(beamMesh);
      }
    });

    // Populate instance matrices
    const tempObj = new THREE.Object3D();
    
    // Tracks current offset indices
    const baseIndices: Record<string, number> = {};
    const detailIndices: Record<string, number> = {};
    tileTypes.forEach(t => {
      baseIndices[t] = 0;
      detailIndices[t] = 0;
    });

    for (let z = 0; z < gridHeight; z++) {
      for (let x = 0; x < gridWidth; x++) {
        const type = grid[z][x];
        const baseMesh = baseInstancedMeshes[type];
        if (!baseMesh) continue;

        const posX = x - halfWidth + 0.5;
        const posZ = z - halfHeight + 0.5;

        // Position base ground tiles
        tempObj.position.set(posX, 0.0, posZ);
        tempObj.scale.set(1, 1, 1);
        
        // Lower river base slightly
        if (type === "River") {
          tempObj.position.y = -0.1;
        }

        tempObj.updateMatrix();
        baseMesh.setMatrixAt(baseIndices[type]++, tempObj.matrix);

        // Position details
        const details = detailInstancedMeshes[type];
        if (details.length === 0) continue;

        const baseIdx = detailIndices[type];

        if (type === "Forest") {
          const trunkMesh = details[0];
          const leafMesh = details[1];
          // Plant 2 trees with slight random offsets
          random.seed(x * 13 + z * 37);
          
          for (let t = 0; t < 2; t++) {
            const ox = random.uniform(-0.2, 0.2);
            const oz = random.uniform(-0.2, 0.2);
            const scale = random.uniform(0.75, 1.25);

            // Trunk
            tempObj.position.set(posX + ox, 0.25, posZ + oz);
            tempObj.scale.set(scale, scale, scale);
            tempObj.updateMatrix();
            trunkMesh.setMatrixAt(baseIdx * 2 + t, tempObj.matrix);

            // Leaves
            tempObj.position.set(posX + ox, 0.65 * scale, posZ + oz);
            tempObj.scale.set(scale, scale, scale);
            tempObj.updateMatrix();
            leafMesh.setMatrixAt(baseIdx * 2 + t, tempObj.matrix);
          }

        } else if (type === "Village") {
          const houseMesh = details[0];
          const roofMesh = details[1];

          // House Base
          tempObj.position.set(posX, 0.3, posZ);
          tempObj.scale.set(1, 1, 1);
          tempObj.updateMatrix();
          houseMesh.setMatrixAt(baseIdx, tempObj.matrix);

          // Roof (rotate a bit for realism)
          tempObj.position.set(posX, 0.55, posZ);
          tempObj.rotation.set(0, Math.PI / 4, 0);
          tempObj.updateMatrix();
          roofMesh.setMatrixAt(baseIdx, tempObj.matrix);
          tempObj.rotation.set(0, 0, 0); // Reset

        } else if (type === "Town") {
          const buildMesh = details[0];
          tempObj.position.set(posX, 0.7, posZ);
          tempObj.updateMatrix();
          buildMesh.setMatrixAt(baseIdx, tempObj.matrix);

        } else if (type === "Mountain") {
          const rockyMesh = details[0];
          const snowMesh = details[1];

          // Rocky Base
          tempObj.position.set(posX, 1.0, posZ);
          tempObj.updateMatrix();
          rockyMesh.setMatrixAt(baseIdx, tempObj.matrix);

          // Snow Cap
          tempObj.position.set(posX, 1.75, posZ);
          tempObj.updateMatrix();
          snowMesh.setMatrixAt(baseIdx, tempObj.matrix);

        } else if (type === "Farm") {
          const cropMesh = details[0];
          // Place 3 rows of crops
          for (let r = 0; r < 3; r++) {
            const offsetZ = -0.25 + r * 0.25;
            tempObj.position.set(posX, 0.12, posZ + offsetZ);
            tempObj.updateMatrix();
            cropMesh.setMatrixAt(baseIdx * 3 + r, tempObj.matrix);
          }

        } else if (type === "Mine") {
          const beamMesh = details[0];
          // Post 1
          tempObj.position.set(posX - 0.2, 0.35, posZ);
          tempObj.updateMatrix();
          beamMesh.setMatrixAt(baseIdx * 3, tempObj.matrix);

          // Post 2
          tempObj.position.set(posX + 0.2, 0.35, posZ);
          tempObj.updateMatrix();
          beamMesh.setMatrixAt(baseIdx * 3 + 1, tempObj.matrix);

          // Crossbeam
          tempObj.position.set(posX, 0.6, posZ);
          tempObj.rotation.set(0, 0, Math.PI / 2);
          tempObj.updateMatrix();
          beamMesh.setMatrixAt(baseIdx * 3 + 2, tempObj.matrix);
          tempObj.rotation.set(0, 0, 0); // Reset
        }

        detailIndices[type]++;
      }
    }

    // Flag update requests
    Object.values(baseInstancedMeshes).forEach(m => m.instanceMatrix.needsUpdate = true);
    Object.values(detailInstancedMeshes).forEach(mList => mList.forEach(m => m.instanceMatrix.needsUpdate = true));

    // 7. Render & Animation Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();

      const time = clock.getElapsedTime();

      // Animate flowing river water (light shifting color/reflection)
      if (riverMaterialRef.current) {
        riverMaterialRef.current.roughness = 0.1 + Math.sin(time * 2.0) * 0.03;
      }

      // Smooth Lerping of agent position and swing animation
      agentsMapRef.current.forEach((agentObj) => {
        const { group, data, visualPos, leftLeg, rightLeg, leftArm, rightArm, body } = agentObj;

        if (!data.is_alive) {
          // Keep dead agent on ground
          group.position.x = data.x - halfWidth + 0.5;
          group.position.z = data.y - halfHeight + 0.5;
          group.position.y = 0.2;
          body.rotation.z = Math.PI / 2; // Lie flat
          return;
        }

        // 1. Calculate Target position
        const targetX = data.x - halfWidth + 0.5;
        const targetZ = data.y - halfHeight + 0.5;
        const targetY = 0.45; // Default ground offset height

        const targetPos = new THREE.Vector3(targetX, targetY, targetZ);

        // 2. Calculate direction & distance
        const diff = new THREE.Vector3().subVectors(targetPos, visualPos);
        const distance = diff.length();

        const speed = 0.085; // Lerp speed

        if (distance > 0.01) {
          // Moving: Lerp visual coordinates towards target
          visualPos.lerp(targetPos, speed);

          // Face walk direction
          const angle = Math.atan2(diff.x, diff.z);
          group.rotation.y = angle;

          // Swing limbs (procedural walk animation)
          const swingSpeed = 16.0;
          const swingAngle = Math.sin(time * swingSpeed) * 0.45;

          leftLeg.rotation.x = swingAngle;
          rightLeg.rotation.x = -swingAngle;
          leftArm.rotation.x = -swingAngle;
          rightArm.rotation.x = swingAngle;

          // Subtle head bob
          body.position.y = Math.sin(time * swingSpeed * 2.0) * 0.04;
        } else {
          // Stationary: Reset rotation and position smoothly
          leftLeg.rotation.x += (0 - leftLeg.rotation.x) * 0.15;
          rightLeg.rotation.x += (0 - rightLeg.rotation.x) * 0.15;
          leftArm.rotation.x += (0 - leftArm.rotation.x) * 0.15;
          rightArm.rotation.x += (0 - rightArm.rotation.x) * 0.15;
          body.position.y += (0 - body.position.y) * 0.15;

          // Pulsing scale for starving agents
          if (data.starving) {
            const scale = 1.0 + Math.sin(time * 8) * 0.12;
            group.scale.set(scale, scale, scale);
          } else {
            group.scale.set(1, 1, 1);
          }

          // Bobbing selected agent
          if (data.id === selectedAgentId) {
            group.position.y = targetY + 0.4 + Math.sin(time * 5) * 0.15;
          } else {
            group.position.y = targetY;
          }
        }

        // Apply updated visual position coordinates to mesh group
        group.position.x = visualPos.x;
        group.position.z = visualPos.z;
        if (data.id !== selectedAgentId) {
          group.position.y = visualPos.y;
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
      baseGeo.dispose();
      
      // Cleanup all materials and geometries
      Object.values(baseInstancedMeshes).forEach(m => {
        m.geometry.dispose();
        if (Array.isArray(m.material)) m.material.forEach(mat => mat.dispose());
        else m.material.dispose();
      });
      Object.values(detailInstancedMeshes).forEach(mList => {
        mList.forEach(m => {
          m.geometry.dispose();
          if (Array.isArray(m.material)) m.material.forEach(mat => mat.dispose());
          else m.material.dispose();
        });
      });
    };
  }, [grid]);

  // Handle Agents creation, deletion, and WebSocket sync updates
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    const currentAgentMap = agentsMapRef.current;
    const incomingAgentIds = new Set(agents.map(a => a.id));

    // Cleanup dead/missing agents
    currentAgentMap.forEach((val, id) => {
      if (!incomingAgentIds.has(id)) {
        scene.remove(val.group);
        val.group.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.geometry.dispose();
            child.material.dispose();
          }
        });
        currentAgentMap.delete(id);
      }
    });

    // Spawn or update agents
    agents.forEach((agent) => {
      const posX = agent.x - halfWidth + 0.5;
      const posZ = agent.y - halfHeight + 0.5;
      const posY = 0.45;

      if (currentAgentMap.has(agent.id)) {
        // Update data binding
        const agentObj = currentAgentMap.get(agent.id)!;
        agentObj.data = agent;

        // If selection marker needs to be appended/synchronized
        const marker = agentObj.group.getObjectByName("selectionRing");
        if (agent.id === selectedAgentId) {
          if (!marker) {
            const ringGeo = new THREE.RingGeometry(0.45, 0.52, 16);
            ringGeo.rotateX(-Math.PI / 2);
            const ringMat = new THREE.MeshBasicMaterial({ color: 0x6366f1, side: THREE.DoubleSide });
            const ringMesh = new THREE.Mesh(ringGeo, ringMat);
            ringMesh.name = "selectionRing";
            ringMesh.position.y = -0.3;
            agentObj.group.add(ringMesh);
          }
        } else {
          if (marker) {
            agentObj.group.remove(marker);
          }
        }
      } else {
        // Build a highly detailed, cute low-poly character model:
        const agentGroup = new THREE.Group();
        
        // Head
        const headGeo = new THREE.SphereGeometry(0.15, 8, 8);
        const headMat = new THREE.MeshStandardMaterial({ color: 0xffdbac, roughness: 0.6 }); // flesh tone
        const headMesh = new THREE.Mesh(headGeo, headMat);
        headMesh.position.y = 0.42;

        // Body Capsule
        const bodyGeo = new THREE.CylinderGeometry(0.15, 0.12, 0.35, 8);
        const roleColor = new THREE.Color(ROLE_COLORS[agent.role] || "#e5e7eb");
        const bodyMat = new THREE.MeshStandardMaterial({ color: roleColor, roughness: 0.5 });
        const bodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
        bodyMesh.name = "agentBodyMesh";
        bodyMesh.position.y = 0.2;
        bodyMesh.userData = { agentId: agent.id }; // For Raycaster selection

        // Limbs Geometries & Materials
        const limbGeo = new THREE.BoxGeometry(0.06, 0.2, 0.06);
        const limbMat = new THREE.MeshStandardMaterial({ color: roleColor, roughness: 0.6 });

        // Left Leg
        const leftLeg = new THREE.Mesh(limbGeo, limbMat);
        leftLeg.position.set(-0.07, 0.0, 0.0);
        // Pivot point offset
        leftLeg.geometry.translate(0, -0.08, 0);

        // Right Leg
        const rightLeg = new THREE.Mesh(limbGeo, limbMat);
        rightLeg.position.set(0.07, 0.0, 0.0);
        rightLeg.geometry.translate(0, -0.08, 0);

        // Left Arm
        const leftArm = new THREE.Mesh(limbGeo, limbMat);
        leftArm.position.set(-0.16, 0.25, 0.0);
        leftArm.geometry.translate(0, -0.08, 0);

        // Right Arm
        const rightArm = new THREE.Mesh(limbGeo, limbMat);
        rightArm.position.set(0.16, 0.25, 0.0);
        rightArm.geometry.translate(0, -0.08, 0);

        // Assemble Character hierarchy
        agentGroup.add(bodyMesh);
        agentGroup.add(headMesh);
        agentGroup.add(leftLeg);
        agentGroup.add(rightLeg);
        agentGroup.add(leftArm);
        agentGroup.add(rightArm);

        // Add Selection indicator
        if (agent.id === selectedAgentId) {
          const ringGeo = new THREE.RingGeometry(0.45, 0.52, 16);
          ringGeo.rotateX(-Math.PI / 2);
          const ringMat = new THREE.MeshBasicMaterial({ color: 0x6366f1, side: THREE.DoubleSide });
          const ringMesh = new THREE.Mesh(ringGeo, ringMat);
          ringMesh.name = "selectionRing";
          ringMesh.position.y = -0.3;
          agentGroup.add(ringMesh);
        }

        scene.add(agentGroup);

        currentAgentMap.set(agent.id, {
          group: agentGroup,
          data: agent,
          visualPos: new THREE.Vector3(posX, posY, posZ),
          leftLeg,
          rightLeg,
          leftArm,
          rightArm,
          body: bodyMesh,
        });
      }
    });
  }, [agents, selectedAgentId]);

  // Click Raycaster for agent selection
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const camera = cameraRef.current;
    const scene = sceneRef.current;
    if (!canvas || !camera || !scene) return;

    const rect = canvas.getBoundingClientRect();
    mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    raycasterRef.current.setFromCamera(mouseRef.current, camera);

    const meshesToIntersect: THREE.Object3D[] = [];
    agentsMapRef.current.forEach(({ group }) => {
      const body = group.getObjectByName("agentBodyMesh");
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
    agentsMapRef.current.forEach(({ group }) => {
      const body = group.getObjectByName("agentBodyMesh");
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
      {/* HUD Instructions */}
      <div className="absolute top-4 right-4 z-10 bg-slate-900/90 border border-slate-700/60 p-3 rounded-lg backdrop-blur-md text-[11px] text-slate-300 pointer-events-none">
        <h4 className="font-bold text-slate-100 mb-1">Controls</h4>
        <p>🖱️ Drag Left: Rotate Camera</p>
        <p>🖱️ Drag Right: Pan Satellite</p>
        <p>⚙️ Scroll: Zoom Altitude</p>
        <p>👤 Click Character: View Details</p>
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
            Activity: {hoveredAgent.last_action}
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

// Seedable random number generator for deterministic forest layout
const random = {
  _seed: 1,
  seed: (val: number) => {
    random._seed = val;
  },
  next: () => {
    const x = Math.sin(random._seed++) * 10000;
    return x - Math.floor(x);
  },
  uniform: (min: number, max: number) => {
    return min + random.next() * (max - min);
  }
};
