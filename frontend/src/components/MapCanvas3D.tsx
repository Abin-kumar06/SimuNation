import React, { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text, Environment, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';

// --- Types ---
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
  profession?: string;
  activity?: string;
}

interface MapCanvas3DProps {
  grid: string[][];
  agents: AgentData[];
  selectedAgentId: number | null;
  onSelectAgent: (agent: AgentData | null) => void;
  worldData: any;
}

const ROLE_COLORS: Record<string, string> = {
  Farmer: '#4caf50',
  Miner: '#ff9800',
  Builder: '#9c27b0',
  Doctor: '#e91e63',
  Teacher: '#2196f3',
  Worker: '#ffc107',
  Trader: '#ffeb3b',
  Merchant: '#00bcd4',
  Child: '#cfd8dc',
  Unemployed: '#9ca3af',
};

// --- Terrain Component (Optimized) ---
interface TerrainProps {
  width: number;
  height: number;
  heightmap: number[][];
  maxHeight: number;
  season: string;
}

const TerrainBase: React.FC<TerrainProps> = ({ width, height, heightmap, season }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  
  const seasonColors: Record<string, string> = {
    spring: '#15803d', // Vibrant green
    summer: '#166534', // Rich forest green
    autumn: '#854d0e', // Golden brown
    winter: '#e2e8f0', // Snowy white
  };

  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(width, height, width - 1, height - 1);
    geo.rotateX(-Math.PI / 2); // Lay flat
    
    // Displace vertices using heightmap
    const positions = geo.attributes.position.array as Float32Array;
    for (let i = 0; i < positions.length; i += 3) {
      const x = positions[i];
      const z = positions[i + 2]; // In Three.js, Y is up, so Z is depth
      
      // Map to heightmap index
      const hx = Math.floor((x + width / 2) / width * (heightmap[0].length - 1));
      const hy = Math.floor((z + height / 2) / height * (heightmap.length - 1));
      
      if (hy >= 0 && hy < heightmap.length && hx >= 0 && hx < heightmap[0].length) {
        positions[i + 1] = heightmap[hy][hx]; // Y is height
      }
    }
    
    geo.computeVertexNormals();
    return geo;
  }, [width, height, heightmap]);
  
  return (
    <group>
      {/* Terrain Mesh */}
      <mesh ref={meshRef} geometry={geometry} receiveShadow castShadow>
        <meshStandardMaterial color={seasonColors[season] || '#15803d'} roughness={0.95} metalness={0.0} />
      </mesh>
      
      {/* Water Plane at base level */}
      <mesh position={[0, 1.2, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[width * 1.5, height * 1.5]} />
        <meshStandardMaterial color="#0284c7" transparent opacity={0.65} roughness={0.1} metalness={0.15} />
      </mesh>
    </group>
  );
};

export const Terrain = React.memo(TerrainBase, (prev, next) => {
  return prev.season === next.season && prev.width === next.width && prev.height === next.height;
});

// --- Building Component (Optimized) ---
interface BuildingProps {
  x: number;
  y: number; // Z in Three.js (depth)
  z: number; // Y in Three.js (height)
  height: number;
  width: number;
  depth: number;
  color: string;
  groundNormal: [number, number, number];
  foundationDepth: number;
  type: string;
  sign?: string | null;
  rotationY?: number;
}

const BuildingBase: React.FC<BuildingProps> = ({
  x, y, z, height, width, depth, color, groundNormal, foundationDepth, type, sign, rotationY = 0
}) => {
  const rotationQuat = useMemo(() => {
    const normal = new THREE.Vector3(...groundNormal);
    const up = new THREE.Vector3(0, 1, 0);
    const qSlope = new THREE.Quaternion().setFromUnitVectors(up, normal);
    const qYaw = new THREE.Quaternion().setFromAxisAngle(up, rotationY);
    return qSlope.multiply(qYaw);
  }, [groundNormal, rotationY]);

  // Generate building geometry based on type
  const buildingGeometry = useMemo(() => {
    switch (type) {
      case 'house':
        return (
          <>
            {/* Main body */}
            <mesh position={[0, height * 0.35, 0]} castShadow receiveShadow>
              <boxGeometry args={[width, height * 0.7, depth]} />
              <meshStandardMaterial color={color} roughness={0.9} />
            </mesh>
            {/* Roof */}
            <mesh position={[0, height * 0.85, 0]} rotation={[0, Math.PI / 4, 0]} castShadow>
              <coneGeometry args={[Math.max(width, depth) * 0.72, height * 0.3, 4]} />
              <meshStandardMaterial color="#8b4513" roughness={0.9} />
            </mesh>
            {/* Door */}
            <mesh position={[0, height * 0.2 - height * 0.2, depth / 2 + 0.01]}>
              <planeGeometry args={[0.7, 1.4]} />
              <meshStandardMaterial color="#5c2e0b" roughness={0.9} />
            </mesh>
            {/* Chimney */}
            <mesh position={[width / 3, height * 0.75, -depth / 4]} castShadow>
              <boxGeometry args={[0.25, 0.7, 0.25]} />
              <meshStandardMaterial color="#8b4513" />
            </mesh>
          </>
        );
      case 'shop':
        return (
          <>
            {/* Body */}
            <mesh position={[0, height / 2, 0]} castShadow receiveShadow>
              <boxGeometry args={[width, height, depth]} />
              <meshStandardMaterial color={color} roughness={0.8} />
            </mesh>
            {/* Large storefront window */}
            <mesh position={[0, height * 0.3, depth / 2 + 0.02]}>
              <planeGeometry args={[width * 0.7, height * 0.4]} />
              <meshStandardMaterial color="#87ceeb" transparent opacity={0.65} emissive="#87ceeb" emissiveIntensity={0.2} />
            </mesh>
            {/* Door */}
            <mesh position={[width / 3, height * 0.3, depth / 2 + 0.02]}>
              <planeGeometry args={[0.7, height * 0.6]} />
              <meshStandardMaterial color="#5c2e0b" />
            </mesh>
            {/* Awning */}
            <mesh position={[0, height * 0.65, depth / 2 + 0.25]} rotation={[0.2, 0, 0]}>
              <boxGeometry args={[width * 0.9, 0.08, 0.5]} />
              <meshStandardMaterial color="#ef4444" />
            </mesh>
          </>
        );
      case 'bank':
        return (
          <>
            <mesh position={[0, height / 2, 0]} castShadow receiveShadow>
              <boxGeometry args={[width, height, depth]} />
              <meshStandardMaterial color={color} roughness={0.4} metalness={0.2} />
            </mesh>
            {/* Columns */}
            {[-width / 3.2, 0, width / 3.2].map((cx, i) => (
              <mesh key={i} position={[cx, height * 0.42, depth / 2 + 0.15]} castShadow>
                <cylinderGeometry args={[0.12, 0.12, height * 0.8, 8]} />
                <meshStandardMaterial color="#e2e8f0" />
              </mesh>
            ))}
            {/* Steps */}
            <mesh position={[0, 0.1, depth / 2 + 0.3]}>
              <boxGeometry args={[width * 0.85, 0.16, 0.7]} />
              <meshStandardMaterial color="#94a3b8" />
            </mesh>
          </>
        );
      case 'school':
        return (
          <>
            <mesh position={[0, height / 2, 0]} castShadow receiveShadow>
              <boxGeometry args={[width, height, depth]} />
              <meshStandardMaterial color={color} roughness={0.85} />
            </mesh>
            {/* Flagpole */}
            <mesh position={[width / 2 - 0.4, height / 2 + 0.6, depth / 2 - 0.4]} castShadow>
              <cylinderGeometry args={[0.03, 0.03, height + 1.2, 8]} />
              <meshStandardMaterial color="#94a3b8" metalness={0.7} />
            </mesh>
            {/* Flag */}
            <mesh position={[width / 2 - 0.4, height + 1.0, depth / 2 - 0.4 + 0.25]}>
              <boxGeometry args={[0.02, 0.35, 0.5]} />
              <meshStandardMaterial color="#ef4444" />
            </mesh>
          </>
        );
      case 'factory':
        return (
          <>
            <mesh position={[0, height / 2, 0]} castShadow receiveShadow>
              <boxGeometry args={[width, height, depth]} />
              <meshStandardMaterial color={color} roughness={0.9} />
            </mesh>
            {/* Smokestack */}
            <mesh position={[width / 3.2, height + 1.2, -depth / 3.2]} castShadow>
              <cylinderGeometry args={[0.22, 0.35, 2.4, 8]} />
              <meshStandardMaterial color="#475569" />
            </mesh>
            {/* Smoke particles */}
            {[0, 1, 2].map((i) => (
              <mesh key={i} position={[width / 3.2, height + 2.5 + i * 0.4, -depth / 3.2 + i * 0.1]}>
                <sphereGeometry args={[0.2 + i * 0.08, 6, 6]} />
                <meshStandardMaterial color="#64748b" transparent opacity={0.6 - i * 0.15} />
              </mesh>
            ))}
          </>
        );
      case 'gas_station':
        return (
          <>
            <mesh position={[-width * 0.15, height / 2, -depth * 0.15]} castShadow receiveShadow>
              <boxGeometry args={[width * 0.6, height, depth * 0.6]} />
              <meshStandardMaterial color={color} />
            </mesh>
            {/* Canopy */}
            <mesh position={[0, height * 0.9, depth * 0.2]} castShadow>
              <boxGeometry args={[width * 0.95, 0.12, depth * 0.65]} />
              <meshStandardMaterial color="#ef4444" />
            </mesh>
            {/* Support pillars */}
            {[-width * 0.4, width * 0.4].map((px, i) => (
              <mesh key={i} position={[px, height * 0.45, depth * 0.45]} castShadow>
                <cylinderGeometry args={[0.07, 0.07, height * 0.9, 8]} />
                <meshStandardMaterial color="#cbd5e1" />
              </mesh>
            ))}
            {/* Gas pump */}
            <mesh position={[0, 0.35, depth * 0.2]} castShadow>
              <boxGeometry args={[0.35, 0.7, 0.25]} />
              <meshStandardMaterial color="#3b82f6" />
            </mesh>
          </>
        );
      case 'apartment':
        return (
          <>
            <mesh position={[0, height / 2, 0]} castShadow receiveShadow>
              <boxGeometry args={[width, height, depth]} />
              <meshStandardMaterial color={color} roughness={0.7} />
            </mesh>
            {/* Grid of windows */}
            {[-0.25, 0.25].map((wx) => 
              [0.2, 0.5, 0.8].map((wy) => (
                <mesh key={`${wx}-${wy}`} position={[width * wx, height * wy, depth / 2 + 0.01]}>
                  <planeGeometry args={[width * 0.2, height * 0.12]} />
                  <meshStandardMaterial color="#87ceeb" emissive="#87ceeb" emissiveIntensity={0.25} />
                </mesh>
              ))
            )}
          </>
        );
      case 'hospital':
        return (
          <>
            <mesh position={[0, height / 2, 0]} castShadow receiveShadow>
              <boxGeometry args={[width, height, depth]} />
              <meshStandardMaterial color={color} roughness={0.6} />
            </mesh>
            {/* Red Cross sign */}
            <group position={[0, height * 0.65, depth / 2 + 0.02]}>
              <mesh>
                <planeGeometry args={[0.8, 0.22]} />
                <meshStandardMaterial color="#ef4444" />
              </mesh>
              <mesh rotation={[0, 0, Math.PI / 2]}>
                <planeGeometry args={[0.8, 0.22]} />
                <meshStandardMaterial color="#ef4444" />
              </mesh>
            </group>
          </>
        );
      case 'barn':
        return (
          <>
            {/* Barn main structure */}
            <mesh position={[0, height * 0.4, 0]} castShadow receiveShadow>
              <boxGeometry args={[width, height * 0.8, depth]} />
              <meshStandardMaterial color={color} roughness={0.95} />
            </mesh>
            {/* Gambrel Roof */}
            <mesh position={[0, height * 0.9, 0]} rotation={[0, 0, 0]} castShadow>
              <boxGeometry args={[width * 1.05, height * 0.25, depth * 1.02]} />
              <meshStandardMaterial color="#5c2e0b" roughness={0.9} />
            </mesh>
            {/* Large barn doors */}
            <mesh position={[0, height * 0.3, depth / 2 + 0.01]}>
              <planeGeometry args={[width * 0.5, height * 0.5]} />
              <meshStandardMaterial color="#451a03" roughness={0.9} />
            </mesh>
          </>
        );
      default:
        return (
          <mesh position={[0, height / 2, 0]} castShadow receiveShadow>
            <boxGeometry args={[width, height, depth]} />
            <meshStandardMaterial color={color} roughness={0.8} />
          </mesh>
        );
    }
  }, [type, height, width, depth, color]);

  return (
    <group position={[x, z, y]} quaternion={rotationQuat}>
      {/* Foundation */}
      <mesh position={[0, -foundationDepth / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[width * 1.08, foundationDepth, depth * 1.08]} />
        <meshStandardMaterial color="#334155" roughness={1.0} />
      </mesh>

      {buildingGeometry}

      {/* Sign */}
      {sign && (
        <Text
          position={[0, height + 0.45, depth / 2 + 0.06]}
          fontSize={0.25}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.02}
          outlineColor="#fef08a"
        >
          {sign}
        </Text>
      )}
    </group>
  );
};

export const Building = React.memo(BuildingBase, (prev, next) => {
  return prev.x === next.x && prev.y === next.y && prev.z === next.z && prev.color === next.color && prev.sign === next.sign && prev.rotationY === next.rotationY;
});

// --- Road Component (Optimized) ---
interface RoadProps {
  elevation_profile: Array<[number, number, number]>;
  width: number;
  type: string;
}

const RoadBase: React.FC<RoadProps> = ({ elevation_profile, width, type }) => {
  const isPaved = type === 'paved' || type === 'highway';
  const roadColor = type === 'highway' ? '#1e293b' : isPaved ? '#334155' : '#78350f';

  const roadGeometries = useMemo(() => {
    if (!elevation_profile || elevation_profile.length < 2) return null;

    const points = elevation_profile.map(([px, py, pz]) => new THREE.Vector3(px - 50, pz + 0.03, py - 50));
    const curve = new THREE.CatmullRomCurve3(points);

    // 1. Road Surface
    const shape = new THREE.Shape();
    shape.moveTo(-width / 2, 0);
    shape.lineTo(width / 2, 0);
    shape.lineTo(width / 2, 0.02);
    shape.lineTo(-width / 2, 0.02);
    shape.closePath();
    const roadGeo = new THREE.ExtrudeGeometry(shape, {
      steps: elevation_profile.length * 2,
      extrudePath: curve,
      bevelEnabled: false,
    });

    // 2. Yellow Center Line (for paved roads)
    let lineGeo = null;
    if (isPaved) {
      const lineShape = new THREE.Shape();
      lineShape.moveTo(-0.06, 0);
      lineShape.lineTo(0.06, 0);
      lineShape.lineTo(0.06, 0.025);
      lineShape.lineTo(-0.06, 0.025);
      lineShape.closePath();
      lineGeo = new THREE.ExtrudeGeometry(lineShape, {
        steps: elevation_profile.length * 2,
        extrudePath: curve,
        bevelEnabled: false,
      });
    }

    // 3. Sidewalks (for paved/highway roads)
    let leftSidewalkGeo = null;
    let rightSidewalkGeo = null;
    if (isPaved) {
      const swWidth = 0.5;
      const leftSwShape = new THREE.Shape();
      leftSwShape.moveTo(-width/2 - swWidth, 0);
      leftSwShape.lineTo(-width/2, 0);
      leftSwShape.lineTo(-width/2, 0.05);
      leftSwShape.lineTo(-width/2 - swWidth, 0.05);
      leftSwShape.closePath();
      leftSidewalkGeo = new THREE.ExtrudeGeometry(leftSwShape, {
        steps: elevation_profile.length * 2,
        extrudePath: curve,
        bevelEnabled: false,
      });

      const rightSwShape = new THREE.Shape();
      rightSwShape.moveTo(width/2, 0);
      rightSwShape.lineTo(width/2 + swWidth, 0);
      rightSwShape.lineTo(width/2 + swWidth, 0.05);
      rightSwShape.lineTo(width/2, 0.05);
      rightSwShape.closePath();
      rightSidewalkGeo = new THREE.ExtrudeGeometry(rightSwShape, {
        steps: elevation_profile.length * 2,
        extrudePath: curve,
        bevelEnabled: false,
      });
    }

    return { roadGeo, lineGeo, leftSidewalkGeo, rightSidewalkGeo };
  }, [elevation_profile, width, isPaved]);

  // Generate street lamps along the curve
  const streetLamps = useMemo(() => {
    if (!isPaved || !elevation_profile || elevation_profile.length < 2) return [];
    
    const lamps = [];
    let accumulatedDist = 0;
    
    for (let i = 1; i < elevation_profile.length - 1; i++) {
      const p1 = elevation_profile[i-1];
      const p2 = elevation_profile[i];
      const dist = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
      accumulatedDist += dist;
      
      if (accumulatedDist >= 12) {
        accumulatedDist = 0;
        
        // Direction vector of the segment
        const dx = p2[0] - p1[0];
        const dy = p2[1] - p1[1];
        const len = Math.hypot(dx, dy);
        if (len > 0.01) {
          const perpX = -dy / len;
          const perpY = dx / len;
          
          // Place lamp on right side
          const offsetDist = width / 2 + 0.4;
          const lx = p2[0] + perpX * offsetDist - 50;
          const ly = p2[1] + perpY * offsetDist - 50;
          const lz = p2[2];
          
          lamps.push({ x: lx, y: ly, z: lz, dirX: perpX, dirY: perpY });
        }
      }
    }
    return lamps;
  }, [elevation_profile, width, isPaved]);

  if (!roadGeometries) return null;

  return (
    <group>
      {/* Road surface */}
      <mesh geometry={roadGeometries.roadGeo} receiveShadow>
        <meshStandardMaterial color={roadColor} roughness={0.95} />
      </mesh>

      {/* Center line */}
      {isPaved && roadGeometries.lineGeo && (
        <mesh geometry={roadGeometries.lineGeo}>
          <meshStandardMaterial color="#fbbf24" roughness={0.9} />
        </mesh>
      )}

      {/* Sidewalks */}
      {isPaved && roadGeometries.leftSidewalkGeo && roadGeometries.rightSidewalkGeo && (
        <>
          <mesh geometry={roadGeometries.leftSidewalkGeo} receiveShadow>
            <meshStandardMaterial color="#cbd5e1" roughness={0.9} />
          </mesh>
          <mesh geometry={roadGeometries.rightSidewalkGeo} receiveShadow>
            <meshStandardMaterial color="#cbd5e1" roughness={0.9} />
          </mesh>
        </>
      )}

      {/* Street Lamps */}
      {streetLamps.map((lamp, idx) => (
        <group key={`lamp-${idx}`} position={[lamp.x, lamp.z, lamp.y]}>
          {/* Post */}
          <mesh position={[0, 1.5, 0]} castShadow>
            <cylinderGeometry args={[0.04, 0.06, 3, 8]} />
            <meshStandardMaterial color="#475569" metalness={0.6} roughness={0.2} />
          </mesh>
          {/* Arm pointing towards road */}
          <mesh 
            position={[-lamp.dirX * 0.25, 2.95, -lamp.dirY * 0.25]} 
            rotation={[0, Math.atan2(-lamp.dirX, -lamp.dirY), 0]}
          >
            <boxGeometry args={[0.1, 0.1, 0.6]} />
            <meshStandardMaterial color="#475569" metalness={0.6} roughness={0.2} />
          </mesh>
          {/* Light bulb / head */}
          <mesh 
            position={[-lamp.dirX * 0.5, 2.85, -lamp.dirY * 0.5]}
            rotation={[0, Math.atan2(-lamp.dirX, -lamp.dirY), 0]}
          >
            <boxGeometry args={[0.2, 0.15, 0.3]} />
            <meshStandardMaterial color="#e2e8f0" emissive="#fef08a" emissiveIntensity={0.8} />
          </mesh>
        </group>
      ))}
    </group>
  );
};

export const Road = React.memo(RoadBase, (prev, next) => {
  return prev.width === next.width && prev.type === next.type && prev.elevation_profile.length === next.elevation_profile.length;
});

// --- Vehicle Component ---
interface VehicleProps {
  x: number;
  y: number; // Z in Three.js
  color: string;
  type: string;
  heightmap: number[][];
  terrainWidth: number;
  terrainHeight: number;
  rotation?: number;
}

export const Vehicle: React.FC<VehicleProps> = ({
  x, y, color, type, heightmap, terrainWidth, terrainHeight, rotation = 0
}) => {
  const wheelsRef = useRef<THREE.Group>(null);

  // Sample terrain height at vehicle position
  const terrainHeightAtPos = useMemo(() => {
    const hx = Math.floor((x + terrainWidth / 2) / terrainWidth * (heightmap[0].length - 1));
    const hy = Math.floor((y + terrainHeight / 2) / terrainHeight * (heightmap.length - 1));
    if (hy >= 0 && hy < heightmap.length && hx >= 0 && hx < heightmap[0].length) {
      return heightmap[hy][hx];
    }
    return 0.2;
  }, [x, y, heightmap, terrainWidth, terrainHeight]);

  useFrame(() => {
    if (wheelsRef.current) {
      wheelsRef.current.children.forEach((wheel) => {
        wheel.rotation.x += 0.18; // Spin wheels
      });
    }
  });

  const isEmergency = type === 'ambulance' || type === 'police';
  const isBus = type === 'bus';
  const isTruck = type === 'truck';

  const bodySize = useMemo(() => {
    if (isBus) return { w: 1.2, h: 0.9, d: 3.2 };
    if (isTruck) return { w: 1.1, h: 0.9, d: 2.8 };
    if (isEmergency) return { w: 0.95, h: 0.7, d: 2.0 };
    return { w: 0.85, h: 0.5, d: 1.7 }; // car
  }, [type, isBus, isTruck, isEmergency]);

  return (
    <group position={[x, terrainHeightAtPos + 0.15, y]} rotation={[0, rotation + Math.PI, 0]}>
      {/* Main body */}
      <group>
        {type === 'bus' && (
          <>
            {/* Bus body */}
            <mesh position={[0, 0.45, 0]} castShadow>
              <boxGeometry args={[bodySize.w, bodySize.h, bodySize.d]} />
              <meshStandardMaterial color={color} metalness={0.2} roughness={0.5} />
            </mesh>
            {/* Windows strip */}
            <mesh position={[bodySize.w/2 + 0.01, 0.55, 0]}>
              <planeGeometry args={[bodySize.d * 0.8, 0.35]} />
              <meshStandardMaterial color="#87CEEB" transparent opacity={0.6} />
            </mesh>
            <mesh position={[-bodySize.w/2 - 0.01, 0.55, 0]} rotation={[0, Math.PI, 0]}>
              <planeGeometry args={[bodySize.d * 0.8, 0.35]} />
              <meshStandardMaterial color="#87CEEB" transparent opacity={0.6} />
            </mesh>
            {/* Windshield */}
            <mesh position={[0, 0.55, bodySize.d/2 + 0.01]}>
              <planeGeometry args={[bodySize.w * 0.8, 0.45]} />
              <meshStandardMaterial color="#87CEEB" transparent opacity={0.6} />
            </mesh>
          </>
        )}

        {type === 'truck' && (
          <>
            {/* Truck cab */}
            <mesh position={[0, 0.4, bodySize.d * 0.3]} castShadow>
              <boxGeometry args={[bodySize.w * 0.95, bodySize.h, bodySize.d * 0.4]} />
              <meshStandardMaterial color={color} metalness={0.3} roughness={0.4} />
            </mesh>
            {/* Windshield */}
            <mesh position={[0, 0.5, bodySize.d * 0.3 + bodySize.d * 0.2 + 0.01]}>
              <planeGeometry args={[bodySize.w * 0.8, 0.35]} />
              <meshStandardMaterial color="#87CEEB" transparent opacity={0.6} />
            </mesh>
            {/* Truck cargo container */}
            <mesh position={[0, 0.5, -bodySize.d * 0.2]} castShadow>
              <boxGeometry args={[bodySize.w, bodySize.h * 1.1, bodySize.d * 0.6]} />
              <meshStandardMaterial color="#64748b" roughness={0.8} />
            </mesh>
          </>
        )}

        {isEmergency && (
          <>
            {/* Emergency Vehicle body */}
            <mesh position={[0, 0.35, 0]} castShadow>
              <boxGeometry args={[bodySize.w, bodySize.h, bodySize.d]} />
              <meshStandardMaterial color={color} metalness={0.3} roughness={0.4} />
            </mesh>
            {/* Windows */}
            <mesh position={[0, 0.5, bodySize.d * 0.2]} castShadow>
              <boxGeometry args={[bodySize.w * 0.9, bodySize.h * 0.4, bodySize.d * 0.4]} />
              <meshStandardMaterial color="#1e293b" />
            </mesh>
            {/* Flashing Light Bar */}
            <mesh position={[0, bodySize.h + 0.15, 0]}>
              <boxGeometry args={[bodySize.w * 0.7, 0.1, 0.25]} />
              <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={2.0} />
            </mesh>
          </>
        )}

        {!isBus && !isTruck && !isEmergency && (
          <>
            {/* Car body - lower */}
            <mesh position={[0, 0.2, 0]} castShadow>
              <boxGeometry args={[bodySize.w, bodySize.h, bodySize.d]} />
              <meshStandardMaterial color={color} metalness={0.3} roughness={0.4} />
            </mesh>
            {/* Car top - cabin */}
            <mesh position={[0, 0.45, -bodySize.d * 0.1]} castShadow>
              <boxGeometry args={[bodySize.w * 0.85, bodySize.h * 0.7, bodySize.d * 0.55]} />
              <meshStandardMaterial color={color} metalness={0.3} roughness={0.4} />
            </mesh>
            {/* Windshield */}
            <mesh position={[0, 0.45, bodySize.d * 0.18]} rotation={[-0.4, 0, 0]}>
              <planeGeometry args={[bodySize.w * 0.75, bodySize.h * 0.5]} />
              <meshStandardMaterial color="#87CEEB" transparent opacity={0.6} />
            </mesh>
          </>
        )}

        {/* Headlights */}
        <mesh position={[bodySize.w * 0.35, 0.2, bodySize.d/2 + 0.01]}>
          <sphereGeometry args={[0.08, 8, 8]} />
          <meshStandardMaterial color="#FFFFE0" emissive="#FFFFE0" emissiveIntensity={0.8} />
        </mesh>
        <mesh position={[-bodySize.w * 0.35, 0.2, bodySize.d/2 + 0.01]}>
          <sphereGeometry args={[0.08, 8, 8]} />
          <meshStandardMaterial color="#FFFFE0" emissive="#FFFFE0" emissiveIntensity={0.8} />
        </mesh>
        
        {/* Taillights */}
        <mesh position={[bodySize.w * 0.35, 0.2, -bodySize.d/2 - 0.01]}>
          <sphereGeometry args={[0.07, 8, 8]} />
          <meshStandardMaterial color="#FF0000" emissive="#FF0000" emissiveIntensity={0.5} />
        </mesh>
        <mesh position={[-bodySize.w * 0.35, 0.2, -bodySize.d/2 - 0.01]}>
          <sphereGeometry args={[0.07, 8, 8]} />
          <meshStandardMaterial color="#FF0000" emissive="#FF0000" emissiveIntensity={0.5} />
        </mesh>
      </group>

      {/* Wheels */}
      <group ref={wheelsRef}>
        {[
          [-bodySize.w/2 - 0.02, 0.08, bodySize.d * 0.28],
          [bodySize.w/2 + 0.02, 0.08, bodySize.d * 0.28],
          [-bodySize.w/2 - 0.02, 0.08, -bodySize.d * 0.28],
          [bodySize.w/2 + 0.02, 0.08, -bodySize.d * 0.28]
        ].map((pos, i) => (
          <mesh key={i} position={pos as [number, number, number]} rotation={[0, 0, Math.PI/2]} castShadow>
            <cylinderGeometry args={[0.22, 0.22, 0.14, 12]} />
            <meshStandardMaterial color="#111827" roughness={0.9} />
            {/* Hubcap */}
            <mesh position={[0.08, 0, 0]} rotation={[0, Math.PI/2, 0]}>
              <cylinderGeometry args={[0.12, 0.12, 0.02, 8]} />
              <meshStandardMaterial color="#9ca3af" metalness={0.7} />
            </mesh>
          </mesh>
        ))}
      </group>
    </group>
  );
};

// --- Agent Component ---
interface AgentProps {
  data: any;
  x: number;
  y: number; // Z in Three.js
  isSelected: boolean;
  onClick: (id: number) => void;
  heightmap: number[][];
  terrainWidth: number;
  terrainHeight: number;
}

export const Agent: React.FC<AgentProps> = ({
  data, x, y, isSelected, onClick, heightmap, terrainWidth, terrainHeight
}) => {
  const meshRef = useRef<THREE.Group>(null);

  // Sample terrain height at agent position
  const terrainHeightAtPos = useMemo(() => {
    const hx = Math.floor((x + terrainWidth / 2) / terrainWidth * (heightmap[0].length - 1));
    const hy = Math.floor((y + terrainHeight / 2) / terrainHeight * (heightmap.length - 1));
    if (hy >= 0 && hy < heightmap.length && hx >= 0 && hx < heightmap[0].length) {
      return heightmap[hy][hx];
    }
    return 0.4;
  }, [x, y, heightmap, terrainWidth, terrainHeight]);

  useFrame(() => {
    if (meshRef.current) {
      // Lerp agent position
      meshRef.current.position.x += (x - meshRef.current.position.x) * 0.09;
      meshRef.current.position.z += (y - meshRef.current.position.z) * 0.09;
      meshRef.current.position.y += (terrainHeightAtPos + 0.45 - meshRef.current.position.y) * 0.09;

      const ring = meshRef.current.getObjectByName('selRing');
      if (ring) {
        ring.rotation.z += 0.025;
      }
    }
  });

  const roleColor = ROLE_COLORS[data.profession] || ROLE_COLORS[data.role] || '#ffffff';

  return (
    <group 
      ref={meshRef} 
      position={[x, terrainHeightAtPos + 0.45, y]}
      onClick={(e) => {
        e.stopPropagation();
        onClick(data.id);
      }}
    >
      {/* Body capsule */}
      <mesh castShadow>
        <cylinderGeometry args={[0.15, 0.15, 0.6, 8]} />
        <meshStandardMaterial color={data.starving ? '#ef4444' : roleColor} roughness={0.6} />
      </mesh>

      {/* Head sphere */}
      <mesh position={[0, 0.42, 0]} castShadow>
        <sphereGeometry args={[0.15, 8, 8]} />
        <meshStandardMaterial color="#ffdbac" roughness={0.7} />
      </mesh>

      {/* Floating emoji indicator */}
      {data.activity && data.activity !== 'idle' && (
        <Text
          position={[0, 0.8, 0]}
          fontSize={0.25}
          color="white"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.02}
          outlineColor="black"
        >
          {data.activity === 'farming' ? '🌾' :
           data.activity === 'mining' ? '⛏️' :
           data.activity === 'trading' ? '💰' :
           data.activity === 'resting' ? '💤' :
           data.activity === 'foraging' ? '🌿' :
           data.starving ? '⚠️' : '👤'}
        </Text>
      )}

      {/* Selection Ring */}
      {isSelected && (
        <mesh name="selRing" position={[0, -0.3, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.26, 0.34, 16]} />
          <meshBasicMaterial color="#6366f1" side={THREE.DoubleSide} transparent opacity={0.8} />
        </mesh>
      )}
    </group>
  );
};

// --- Dynamic Lighting ---
const DynamicLighting: React.FC<{ timeOfDay: string }> = ({ timeOfDay }) => {
  const { scene } = useThree();

  useEffect(() => {
    const toRemove: THREE.Object3D[] = [];
    scene.traverse((child) => {
      if (child instanceof THREE.DirectionalLight || child instanceof THREE.AmbientLight || child instanceof THREE.HemisphereLight) {
        toRemove.push(child);
      }
    });
    toRemove.forEach(light => scene.remove(light));

    const configs: Record<string, { sunColor: string; sunIntensity: number; sunPos: [number, number, number]; ambientColor: string; ambientIntensity: number; fogColor: string }> = {
      morning: {
        sunColor: '#fdba74',
        sunIntensity: 1.1,
        sunPos: [30, 25, 30],
        ambientColor: '#c084fc',
        ambientIntensity: 0.45,
        fogColor: '#fef3c7',
      },
      day: {
        sunColor: '#ffffff',
        sunIntensity: 1.4,
        sunPos: [20, 80, 20],
        ambientColor: '#a5f3fc',
        ambientIntensity: 0.55,
        fogColor: '#e2e8f0',
      },
      evening: {
        sunColor: '#f97316',
        sunIntensity: 0.95,
        sunPos: [-30, 20, -30],
        ambientColor: '#312e81',
        ambientIntensity: 0.35,
        fogColor: '#ffedd5',
      },
      night: {
        sunColor: '#38bdf8',
        sunIntensity: 0.15,
        sunPos: [-20, 40, 20],
        ambientColor: '#090d16',
        ambientIntensity: 0.08,
        fogColor: '#020617',
      },
    };

    const config = configs[timeOfDay] || configs.day;

    const sun = new THREE.DirectionalLight(config.sunColor, config.sunIntensity);
    sun.position.set(...config.sunPos);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 1024;
    sun.shadow.mapSize.height = 1024;
    sun.shadow.camera.near = 0.5;
    sun.shadow.camera.far = 180;
    const d = 60;
    sun.shadow.camera.left = -d;
    sun.shadow.camera.right = d;
    sun.shadow.camera.top = d;
    sun.shadow.camera.bottom = -d;
    sun.shadow.bias = -0.0005;
    scene.add(sun);

    const ambient = new THREE.AmbientLight(config.ambientColor, config.ambientIntensity);
    scene.add(ambient);

    scene.fog = new THREE.Fog(config.fogColor, 40, 160);
  }, [timeOfDay, scene]);

  return null;
};

// --- Assembly Scene Component ---
interface TownSceneProps {
  worldData: any;
  selectedAgentId: number | null;
  onAgentClick: (id: number) => void;
}

const TownScene: React.FC<TownSceneProps> = ({ worldData, selectedAgentId, onAgentClick }) => {
  const infra = worldData?.infrastructure || {};
  const terrain = infra.terrain || { width: 100, height: 100, heightmap: [[0]], max_height: 1 };
  const buildings = infra.buildings || [];
  const roads = infra.roads || [];
  const vehicles = infra.vehicles || [];
  
  const timeOfDay = worldData?.time || 'day';
  const season = worldData?.season || 'spring';
  const renderAgents = worldData?.agents || [];

  // Generate seasonal trees scattered around
  const trees = useMemo(() => {
    if (!terrain || !terrain.heightmap) return [];
    const list = [];
    const width = terrain.width;
    const height = terrain.height;
    const heightmap = terrain.heightmap;
    
    let seed = 12345;
    const random = () => {
      const x = Math.sin(seed++) * 10000;
      return x - Math.floor(x);
    };

    // Spawn ~150 trees
    for (let i = 0; i < 150; i++) {
      const rx = random() * (width - 6) - (width / 2 - 3);
      const ry = random() * (height - 6) - (height / 2 - 3);
      
      const hx = Math.floor((rx + width / 2) / width * (heightmap[0].length - 1));
      const hy = Math.floor((ry + height / 2) / height * (heightmap.length - 1));
      
      if (hy >= 0 && hy < heightmap.length && hx >= 0 && hx < heightmap[0].length) {
        const th = heightmap[hy][hx];
        // Only spawn trees on green land, avoiding deep water and mountain tops
        if (th > 1.4 && th < 6.0) {
          list.push({
            id: i,
            x: rx,
            y: ry,
            z: th,
            scale: 0.6 + random() * 0.8,
            type: random() > 0.4 ? 'pine' : 'oak',
          });
        }
      }
    }
    return list;
  }, [terrain]);

  return (
    <>
      <DynamicLighting timeOfDay={timeOfDay} />
      <Terrain 
        width={terrain.width} 
        height={terrain.height} 
        heightmap={terrain.heightmap} 
        maxHeight={terrain.max_height} 
        season={season} 
      />
      
      {/* Roads */}
      {roads.map((road: any, i: number) => (
        <Road key={`road-${i}`} {...road} />
      ))}
      
      {/* Buildings */}
      {buildings.map((b: any) => (
        <Building 
          key={`building-${b.id}`} 
          x={b.x - 50} 
          y={b.y - 50} 
          z={b.z} 
          height={b.height} 
          width={b.width} 
          depth={b.depth} 
          color={b.color} 
          groundNormal={b.ground_normal} 
          foundationDepth={b.foundation_depth} 
          type={b.type} 
          sign={b.sign} 
          rotationY={b.rotation}
        />
      ))}

      {/* Trees */}
      {trees.map((tree) => (
        <group key={`tree-${tree.id}`} position={[tree.x, tree.z, tree.y]} scale={tree.scale}>
          {/* Trunk */}
          <mesh castShadow position={[0, 0.4, 0]}>
            <cylinderGeometry args={[0.06, 0.1, 0.8, 8]} />
            <meshStandardMaterial color="#78350f" roughness={0.9} />
          </mesh>
          {/* Foliage */}
          {tree.type === 'pine' ? (
            <mesh castShadow position={[0, 1.1, 0]}>
              <coneGeometry args={[0.45, 1.2, 5]} />
              <meshStandardMaterial color={season === 'winter' ? '#e2e8f0' : season === 'autumn' ? '#c2410c' : '#14532d'} roughness={0.9} />
            </mesh>
          ) : (
            <mesh castShadow position={[0, 1.0, 0]}>
              <sphereGeometry args={[0.45, 8, 8]} />
              <meshStandardMaterial color={season === 'winter' ? '#cbd5e1' : season === 'autumn' ? '#ca8a04' : '#15803d'} roughness={0.9} />
            </mesh>
          )}
        </group>
      ))}

      {/* Settlement labels */}
      {(infra.settlements || []).map((s: any, idx: number) => {
        const hx = Math.floor((s.x) / terrain.width * (terrain.heightmap[0].length - 1));
        const hy = Math.floor((s.y) / terrain.height * (terrain.heightmap.length - 1));
        let sz = 2.0;
        if (hy >= 0 && hy < terrain.heightmap.length && hx >= 0 && hx < terrain.heightmap[0].length) {
          sz = terrain.heightmap[hy][hx];
        }
        return (
          <group key={`settlement-${idx}`} position={[s.x - 50, sz + 4.5, s.y - 50]}>
            <Text
              fontSize={1.2}
              color="#fbbf24"
              anchorX="center"
              anchorY="middle"
              outlineWidth={0.06}
              outlineColor="#1e293b"
            >
              {s.name}
            </Text>
          </group>
        );
      })}
      
      {/* Vehicles */}
      {vehicles.map((v: any) => (
        <Vehicle 
          key={`vehicle-${v.id}`} 
          x={v.x - 50} 
          y={v.y - 50} 
          color={v.color} 
          type={v.type} 
          heightmap={terrain.heightmap} 
          terrainWidth={terrain.width} 
          terrainHeight={terrain.height} 
          rotation={v.rotation}
        />
      ))}
      
      {/* Agents */}
      {renderAgents.map((a: any) => (
        <Agent 
          key={`agent-${a.id}`} 
          data={a} 
          x={a.x - 50} 
          y={a.y - 50} 
          isSelected={a.id === selectedAgentId} 
          onClick={onAgentClick} 
          heightmap={terrain.heightmap} 
          terrainWidth={terrain.width} 
          terrainHeight={terrain.height} 
        />
      ))}
      
      <ContactShadows position={[0, 0.02, 0]} opacity={0.35} scale={110} blur={2.5} far={4} />
    </>
  );
};

// --- Exported Component ---
export const MapCanvas3D: React.FC<MapCanvas3DProps> = ({
  grid: _grid,
  agents,
  selectedAgentId,
  onSelectAgent,
  worldData,
}) => {
  const handleAgentClick = (agentId: number) => {
    const fullAgentData = agents.find((a) => a.id === agentId);
    if (fullAgentData) {
      onSelectAgent(fullAgentData);
    }
  };

  const isLoading = !worldData || !worldData.infrastructure || !worldData.infrastructure.terrain;

  return (
    <div
      className="relative border border-slate-700/80 rounded-xl overflow-hidden shadow-2xl bg-slate-950 select-none"
      style={{ height: '500px' }}
    >
      {!isLoading && (
        <Canvas
          shadows
          camera={{ position: [50, 45, 55], fov: 42, near: 0.1, far: 500 }}
          style={{ width: '100%', height: '100%' }}
          gl={{ antialias: true }}
          onPointerDown={() => onSelectAgent(null)}
        >
          <TownScene 
            worldData={worldData} 
            selectedAgentId={selectedAgentId} 
            onAgentClick={handleAgentClick}
          />
          <OrbitControls 
            makeDefault
            enablePan
            enableZoom
            enableRotate
            minDistance={10}
            maxDistance={140}
            maxPolarAngle={Math.PI / 2.15}
            target={[0, 0, 0]}
            dampingFactor={0.06}
            enableDamping
          />
          <Environment preset="city" />
        </Canvas>
      )}

      {isLoading && (
        <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-sm flex flex-col items-center justify-center gap-4 text-center p-6 z-20">
          <div className="w-12 h-12 rounded-full border-4 border-indigo-600/30 border-t-indigo-500 animate-spin" />
          <div className="flex flex-col gap-1">
            <h4 className="font-semibold text-slate-100">Generating 3D Town Infrastructure...</h4>
            <span className="text-xs text-slate-400">
              Running simulation step to construct road networks and heightmap layouts.
            </span>
          </div>
        </div>
      )}

      <div className="absolute bottom-4 right-4 bg-slate-900/85 backdrop-blur border border-slate-800 text-[10.5px] text-slate-400 p-2.5 rounded-lg flex flex-col gap-1 pointer-events-none z-10">
        <span className="font-semibold text-slate-200 uppercase tracking-wider mb-0.5">3D Camera Controls</span>
        <div>Left click + Drag to rotate view</div>
        <div>Right click + Drag to pan camera</div>
        <div>Scroll wheel to zoom in/out</div>
        <div>Click agents to inspect stats</div>
      </div>
    </div>
  );
};
