package org.osm2world.core.world.modules;

import static org.osm2world.core.target.common.material.Materials.*;
import static org.osm2world.core.target.common.material.NamedTexCoordFunction.GLOBAL_X_Z;
import static org.osm2world.core.target.common.material.TexCoordUtil.triangleTexCoordLists;

import java.util.Collection;

import org.osm2world.core.map_data.data.MapArea;
import org.osm2world.core.map_data.data.MapNode;
import org.osm2world.core.map_data.data.MapWaySegment;
import org.osm2world.core.map_elevation.data.GroundState;
import org.osm2world.core.math.TriangleXYZ;
import org.osm2world.core.target.RenderableToAllTargets;
import org.osm2world.core.target.Target;
import org.osm2world.core.target.common.material.Material;
import org.osm2world.core.world.data.AbstractAreaWorldObject;
import org.osm2world.core.world.data.NoOutlineWaySegmentWorldObject;
import org.osm2world.core.world.data.NoOutlineNodeWorldObject;
import org.osm2world.core.world.data.TerrainBoundaryWorldObject;
import org.osm2world.core.world.modules.common.AbstractModule;

/**
 * adds parking spaces to the world
 */
public class PointOfInterestModule extends AbstractModule {
	
	@Override
        protected void applyToNode(MapNode node) {

        	if (node.getTags().containsKey("amenity")) {
        	        node.addRepresentation(new PointOfInterestNode(node));
        	}

        }

       	@Override
        protected void applyToWaySegment(MapWaySegment segment) {

        	if (segment.getTags().containsKey("amenity")) {
        	        segment.addRepresentation(new PointOfInterestWay(segment));
        	}

        }

        @Override
        protected void applyToArea(MapArea area) {

        	if (area.getTags().containsKey("amenity")) {
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
