package org.osm2world.core.world.modules;

import static org.osm2world.core.target.common.material.Materials.*;
import static org.osm2world.core.target.common.material.NamedTexCoordFunction.GLOBAL_X_Z;
import static org.osm2world.core.target.common.material.TexCoordUtil.triangleTexCoordLists;

import java.util.*;

import org.osm2world.core.map_data.data.MapArea;
import org.osm2world.core.map_data.data.MapNode;
import org.osm2world.core.map_data.data.MapWaySegment;
import org.osm2world.core.map_data.data.MapElement;
import org.osm2world.core.map_elevation.data.GroundState;
import org.osm2world.core.math.TriangleXYZ;
import org.osm2world.core.target.RenderableToAllTargets;
import org.osm2world.core.target.Target;
import org.osm2world.core.target.common.material.Material;
import org.osm2world.core.target.common.material.Materials;
import org.osm2world.core.world.data.AbstractAreaWorldObject;
import org.osm2world.core.world.data.NoOutlineWaySegmentWorldObject;
import org.osm2world.core.world.data.NoOutlineNodeWorldObject;
import org.osm2world.core.world.data.TerrainBoundaryWorldObject;
import org.osm2world.core.world.modules.common.AbstractModule;

/**
 * Adds a single Point of Interet (Feature Category) to the World
 */
public class PointOfInterestModule extends AbstractModule {
	
        private static final List<String> tagKeys = new ArrayList<String>() {{
		add("amenity"); add("tourism"); add("shop"); add("leisure");
	}};

	private boolean applyToFilterCondition(MapElement element) {
		return element.getTags().containsKey("name") && 
		    element.getTags().containsAnyKey(tagKeys);
	}

	@Override
        protected void applyToNode(MapNode node) {

        	if (applyToFilterCondition(node)) {
        	        node.addRepresentation(new PointOfInterestNode(node));
        	}

        }

       	@Override
        protected void applyToWaySegment(MapWaySegment segment) {

                if (applyToFilterCondition(segment)) {
        	        segment.addRepresentation(new PointOfInterestWay(segment));
        	}

        }

        @Override
        protected void applyToArea(MapArea area) {

                if (applyToFilterCondition(area)) {
        	        area.addRepresentation(new PointOfInterestArea(area));
        	}

        }

        private static class PointOfInterestNode extends NoOutlineNodeWorldObject
						 implements RenderableToAllTargets {

		private MapNode node;

		public PointOfInterestNode(MapNode node) {
			super(node);	
		}		

		@Override
		public void renderTo(Target<?> target) {
			// Steel material (randomly chosen)
			// corners is null to create a round cylinder
			// magic number 1 for the radius &  10 for height of 
			// the cylinder, want to draw the top & bottom, 
			//
			// drawColumn(Material material, Integer corners,
			// VectorXYZ base, double height, double radiusBottom,
			// double radiusTop, boolean drawBottom, boolean drawTop);
                        target.drawColumn(Materials.STEEL, null,
				getBase(), 9, 2, 2, true, true);
		}

		@Override
		public GroundState getGroundState() {
			return GroundState.ON;
		}

	}

	private static class PointOfInterestWay extends NoOutlineWaySegmentWorldObject
						implements RenderableToAllTargets {
	
		private MapWaySegment segment;

		public PointOfInterestWay(MapWaySegment segment) {
			super(segment);	
		}		

		@Override
		public void renderTo(Target<?> target) {

		}

		@Override
		public GroundState getGroundState() {
			return GroundState.ON;
		}

	}
	
	

	private static class PointOfInterestArea extends AbstractAreaWorldObject
						 implements RenderableToAllTargets {
	
		private MapArea area;
	
		public PointOfInterestArea(MapArea area) {
			super(area);	
		}		
	
		@Override
		public void renderTo(Target<?> target) {
	
		}

		@Override
		public GroundState getGroundState() {
			return GroundState.ON;
		}

	}
	
}
