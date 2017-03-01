package org.osm2world.core.target.obj;

import static java.awt.Color.WHITE;
import static java.lang.Math.max;
import static java.util.Collections.nCopies;
import static org.osm2world.core.target.common.material.Material.multiplyColor;

import java.awt.Color;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.openstreetmap.josm.plugins.graphview.core.data.TagGroup;
import org.osm2world.core.map_data.data.MapArea;
import org.osm2world.core.map_data.data.MapElement;
import org.osm2world.core.map_data.data.MapNode;
import org.osm2world.core.map_data.data.MapWaySegment;
import org.osm2world.core.map_elevation.data.EleConnector;
import org.osm2world.core.math.TriangleXYZ;
import org.osm2world.core.math.TriangleXYZWithNormals;
import org.osm2world.core.math.VectorXYZ;
import org.osm2world.core.math.VectorXZ;
import org.osm2world.core.osm.data.OSMElement;
import org.osm2world.core.target.common.FaceTarget;
import org.osm2world.core.target.common.TextureData;
import org.osm2world.core.target.common.material.Material;
import org.osm2world.core.target.common.material.Materials;
import org.osm2world.core.world.data.WorldObject;

public class ObjTarget extends FaceTarget<RenderableToObj> {

	private final PrintStream objStream;
	private final PrintStream mtlStream;
	
	private final Map<VectorXYZ, Integer> vertexIndexMap = new HashMap<VectorXYZ, Integer>();
	private final Map<VectorXYZ, Integer> normalsIndexMap = new HashMap<VectorXYZ, Integer>();
	private final Map<VectorXZ, Integer> texCoordsIndexMap = new HashMap<VectorXZ, Integer>();
	private final Map<Material, String> materialMap = new HashMap<Material, String>();
	
	private Class<? extends WorldObject> currentWOGroup = null;
	private int anonymousWOCounter = 0;
	
	private Material currentMaterial = null;
	private int currentMaterialLayer = 0;
	private static int anonymousMaterialCounter = 0;
	
	// this is approximatly one millimeter
	private static final double SMALL_OFFSET = 1e-3;
	
	public ObjTarget(PrintStream objStream, PrintStream mtlStream) {
		
		this.objStream = objStream;
		this.mtlStream = mtlStream;
				
	}
	
	@Override
	public Class<RenderableToObj> getRenderableType() {
		return RenderableToObj.class;
	}
	
	@Override
	public void render(RenderableToObj renderable) {
		renderable.renderTo(this);
	}
	
	@Override
	public boolean reconstructFaces() {
		return config != null && config.getBoolean("reconstructFaces", false);
	}

	@Override
	public void beginObject(WorldObject object) {
		
		if (object == null) {
			
			currentWOGroup = null;
			objStream.println("g null");
			objStream.println("o null");
			
		} else {
			
			/* maybe start a group depending on the object's class */
			
			if (!object.getClass().equals(currentWOGroup)) {
				currentWOGroup = object.getClass();
				objStream.println("g " + currentWOGroup.getSimpleName());
			}
			
			/* start an object with the object's class
			 * and the underlying OSM element's name/ref tags */
			
			String roadSuffix = null;
			String foodAndDrinkSuffix = null;
			
			MapElement element = object.getPrimaryMapElement();
			OSMElement osmElement;
			if (element instanceof MapNode) {
				osmElement = ((MapNode) element).getOsmNode();
				
				List<MapWaySegment> connectedWaySegments = ((MapNode) element).getConnectedWaySegments();
				int pedestrians = 0;
				for (MapWaySegment mapWaySegment : connectedWaySegments) {
					pedestrians += isPath(mapWaySegment.getTags()) ? 1 : 0;
				}
				if (pedestrians >= (connectedWaySegments.size()+1) / 2) {
					roadSuffix = "::pedestrian";
				}
			} else if (element instanceof MapWaySegment) {
				osmElement = ((MapWaySegment) element).getOsmWay();
			} else if (element instanceof MapArea) {
				osmElement = ((MapArea) element).getOsmObject();
			} else {
				osmElement = null;
			}
			
			if (roadSuffix == null) {
				roadSuffix = isPath(osmElement.tags) ? "::pedestrian" : "";
			}

			if (osmElement != null && osmElement.tags.containsKey("name")) {
				objStream.println("o " + object.getClass().getSimpleName() + " " + osmElement.tags.getValue("name") + roadSuffix + getFeatureCategorysString(osmElement.tags));
			} else if (osmElement != null && osmElement.tags.containsKey("ref")) {
				objStream.println("o " + object.getClass().getSimpleName() + " " + osmElement.tags.getValue("ref") + roadSuffix + getFeatureCategorysString(osmElement.tags));
			} else {
				objStream.println("o " + object.getClass().getSimpleName() + anonymousWOCounter ++ + roadSuffix + getFeatureCategorysString(osmElement.tags));
			}
		}
		
	}
	
	private static boolean isPath(TagGroup tags) {
		String highwayValue = tags.getValue("highway");
		if ("path".equals(highwayValue)
			|| "footway".equals(highwayValue)
			|| "cycleway".equals(highwayValue)
			|| "service".equals(highwayValue)
			|| "bridleway".equals(highwayValue)
			|| "living_street".equals(highwayValue)
			|| "pedestrian".equals(highwayValue)
			|| "track".equals(highwayValue)
			|| "steps".equals(highwayValue)) {
			return true;
		}
		if (tags.containsKey("footway")
				|| tags.contains("tourism", "attraction")
				|| tags.contains("man_made", "pier")
				|| tags.contains("man_made", "breakwater")) {
			return true;
		}
		String footValue = tags.getValue("foot");
		if ("yes".equals(footValue)
			|| "designated".equals(footValue)) {
			return true;
		}
		return false;
	}

        private static final Map<String, Set<String>> featureCategoriesToTags = new HashMap<String, Set<String>>() {{
		put("FoodAndDrink", new HashSet<String>() {{
                	add("bar"); add("bbq"); add("biergarten"); add("cafe"); add("drinking_water"); 
			add("fast_food"); add("food_court"); add("ice_cream"); add("pub"); add("restaurant");	
		}});
                put("Schools", new HashSet<String>() {{
			add("college"); add("kindergarten"); add("library"); add("school"); add("music_school"); 
			add("driving_school"); add("language_school"); add("university");
		}});
		put("Money", new HashSet<String>() {{
			add("bank"); add("atm"); add("bureau_de_change");
		}});
		put("Entertainment", new HashSet<String>() {{
			add("arts_center"); add("brothel"); add("casino"); add("cinema"); add("gambling"); 
			add("studio"); add("community_center"); add("nightclub"); add("planetarium"); 
			add("social_centre"); add("stripclub"); add("theater"); add("swingerclub");
		}});
		put("Medical", new HashSet<String>() {{
			add("clinic"); add("dentist"); add("doctors"); add("hospital"); add("nursing_home"); 
			add("pharmacy"); add("social_facility"); add("veterinary"); add("blood_donation");
		}});
		put("Public", new HashSet<String>() {{
			add("courthouse"); add("embassy"); add("fire_station"); add("internet_cafe");
			add("marketplace"); add("police"); add("post_office"); add("prison"); add("toilets"); 
			add("vending_machine");
		}});
		put("Leisure", new HashSet<String>() {{
 			add("adult_gaming_centre"); add("amusement_arcade"); add("bandstand"); 
			add("beach_resort"); add("common"); add("dance"); add("firepit"); add("fishing"); 
			add("fitness_centre"); add("hackerspace"); add("ice_rink"); add("horse_riding"); 
			add("marina"); add("miniature_golf"); add("picnic_table"); add("sports_centre"); 
			add("stadium"); add("track"); add("summer_camp"); add("water_park");
                }});
		// Tourism & Shopping do not have any value tags to consider
        }};

	// Returns the string of feature categories associated with this tag group, where each category
	// is delimited by a "::"
	private static String getFeatureCategorysString(TagGroup tags) {
		String resultString = "";
		
		String amenityValue = tags.getValue("amenity");
		String tourismValue = tags.getValue("tourism");
		String shoppingValue = tags.getValue("shop");
		String leisureValue = tags.getValue("leisure");

		if (amenityValue != null) {
			// see if we have a foodAndDrink, school, money, entertainment, medical, or public
			if (featureCategoriesToTags.getOrDefault("FoodAndDrink", new HashSet<String>()).contains(amenityValue)) {
				resultString += "::FoodAndDrink";
			}
			if (featureCategoriesToTags.getOrDefault("Schools", new HashSet<String>()).contains(amenityValue)) {
				resultString += "::Schools";
			}
			if (featureCategoriesToTags.getOrDefault("Money", new HashSet<String>()).contains(amenityValue)) {
				resultString += "::Money";
			}
			if (featureCategoriesToTags.getOrDefault("Entertainment", new HashSet<String>()).contains(amenityValue)) {
				resultString += "::Entertainment";
			}
			if (featureCategoriesToTags.getOrDefault("Medical", new HashSet<String>()).contains(amenityValue)) {
				resultString += "::Medical";
			}
			if (featureCategoriesToTags.getOrDefault("Public", new HashSet<String>()).contains(amenityValue)) {
				resultString += "::Public";
			}
		}
		if (tourismValue != null) {
			resultString += "::Tourism";
		}
		if (shoppingValue != null) {
			resultString += "::Shopping";
		}
		if (leisureValue != null && featureCategoriesToTags.getOrDefault("Leisure", new HashSet<String>()).contains(leisureValue)) {
			resultString += "::Leisure";
		}

		return resultString;
	}
	
	@Override
	public void drawFace(Material material, List<VectorXYZ> vs,
			List<VectorXYZ> normals, List<List<VectorXZ>> texCoordLists) {

		int[] normalIndices = null;
		if (normals != null) {
			normalIndices = normalsToIndices(normals);
		}
		
		VectorXYZ faceNormal = new TriangleXYZ(vs.get(0), vs.get(1), vs.get(2)).getNormal();
		
		for (int layer = 0; layer < max(1, material.getNumTextureLayers()); layer++) {
			
			useMaterial(material, layer);
		
			int[] texCoordIndices = null;
			if (texCoordLists != null && !texCoordLists.isEmpty()) {
				texCoordIndices = texCoordsToIndices(texCoordLists.get(layer));
			}
			
			writeFace(verticesToIndices((layer == 0)? vs : offsetVertices(vs, nCopies(vs.size(), faceNormal), layer * SMALL_OFFSET)),
					normalIndices, texCoordIndices);
		}
	}

	@Override
	public void drawTrianglesWithNormals(Material material,
			Collection<? extends TriangleXYZWithNormals> triangles,
			List<List<VectorXZ>> texCoordLists) {
		
		for (int layer = 0; layer < max(1, material.getNumTextureLayers()); layer++) {
			
			useMaterial(material, layer);

			int triangleNumber = 0;
			for (TriangleXYZWithNormals t : triangles) {
			
				int[] texCoordIndices = null;
				if (texCoordLists != null && !texCoordLists.isEmpty()) {
					List<VectorXZ> texCoords = texCoordLists.get(layer);
					texCoordIndices = texCoordsToIndices(
							texCoords.subList(3*triangleNumber, 3*triangleNumber + 3));
				}
				
				writeFace(verticesToIndices((layer == 0)? t.getVertices() : offsetVertices(t.getVertices(), t.getNormals(), layer * SMALL_OFFSET)),
						normalsToIndices(t.getNormals()), texCoordIndices);
			
				triangleNumber ++;
			}
			
		}
		
	}

	private void useMaterial(Material material, int layer) {
		if (!material.equals(currentMaterial) || (layer != currentMaterialLayer)) {
			
			String name = materialMap.get(material);
			if (name == null) {
				name = Materials.getUniqueName(material);
				if (name == null) {
					name = "MAT_" + anonymousMaterialCounter;
					anonymousMaterialCounter += 1;
				}
				materialMap.put(material, name);
				writeMaterial(material, name);
			}
			
			objStream.println("usemtl " + name + "_" + layer);
			
			currentMaterial = material;
			currentMaterialLayer = layer;
		}
	}
	
	private List<? extends VectorXYZ> offsetVertices(List<? extends VectorXYZ> vs, List<VectorXYZ> directions, double offset) {
		
		List<VectorXYZ> result = new ArrayList<VectorXYZ>(vs.size());
		
		for (int i = 0; i < vs.size(); i++) {
			result.add(vs.get(i).add(directions.get(i).mult(offset)));
		}
		
		return result;
	}
	
	private int[] verticesToIndices(List<? extends VectorXYZ> vs) {
		return vectorsToIndices(vertexIndexMap, "v ", vs);
	}

	private int[] normalsToIndices(List<? extends VectorXYZ> normals) {
		return vectorsToIndices(normalsIndexMap, "vn ", normals);
	}

	private int[] texCoordsToIndices(List<VectorXZ> texCoords) {
		return vectorsToIndices(texCoordsIndexMap, "vt ", texCoords);
	}
	
	private <V> int[] vectorsToIndices(Map<V, Integer> indexMap,
			String objLineStart, List<? extends V> vectors) {
		
		int[] indices = new int[vectors.size()];
		
		for (int i=0; i<vectors.size(); i++) {
			final V v = vectors.get(i);
			Integer index = indexMap.get(v);
			if (index == null) {
				index = indexMap.size();
				objStream.println(objLineStart + " " + formatVector(v));
				indexMap.put(v, index);
			}
			indices[i] = index;
		}
		
		return indices;
		
	}
	
	private String formatVector(Object v) {
		
		if (v instanceof VectorXYZ) {
			VectorXYZ vXYZ = (VectorXYZ)v;
			return vXYZ.x + " " + vXYZ.y + " " + (-vXYZ.z);
		} else {
			VectorXZ vXZ = (VectorXZ)v;
			return vXZ.x + " " + vXZ.z;
		}
		
	}

	private void writeFace(int[] vertexIndices, int[] normalIndices,
			int[] texCoordIndices) {

		assert normalIndices == null
				|| vertexIndices.length == normalIndices.length;

		objStream.print("f");

		for (int i = 0; i < vertexIndices.length; i++) {

			objStream.print(" " + (vertexIndices[i]+1));

			if (texCoordIndices != null && normalIndices == null) {
				objStream.print("/" + (texCoordIndices[i]+1));
			} else if (texCoordIndices == null && normalIndices != null) {
				objStream.print("//" + (normalIndices[i]+1));
			} else if (texCoordIndices != null && normalIndices != null) {
				objStream.print("/" + (texCoordIndices[i]+1)
						+ "/" + (normalIndices[i]+1));
			}

		}

		objStream.println();
	}
	
	private void writeMaterial(Material material, String name) {

		for (int i = 0; i < max(1, material.getNumTextureLayers()); i++) {
			
			TextureData textureData = null;
			if (material.getNumTextureLayers() > 0) {
				textureData = material.getTextureDataList().get(i);
			}
		
			mtlStream.println("newmtl " + name + "_" + i);
			
			if (textureData == null || textureData.colorable) {
				writeColorLine("Ka", material.ambientColor());
				writeColorLine("Kd", material.diffuseColor());
				//Ks
				//Ns
			} else {
				writeColorLine("Ka", multiplyColor(WHITE, material.getAmbientFactor()));
				writeColorLine("Kd", multiplyColor(WHITE, 1 - material.getAmbientFactor()));
				//Ks
				//Ns
			}
		
			if (textureData != null) {
				mtlStream.println("map_Ka " + textureData.file);
				mtlStream.println("map_Kd " + textureData.file);
			}
			mtlStream.println();
		}
	}
	
	private void writeColorLine(String lineStart, Color color) {
		
		mtlStream.println(lineStart
				+ " " + color.getRed() / 255f
				+ " " + color.getGreen() / 255f
				+ " " + color.getBlue() / 255f);
		
	}

}
