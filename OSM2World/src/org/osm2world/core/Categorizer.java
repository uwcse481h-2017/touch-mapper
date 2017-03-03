package org.osm2world.core;

import java.lang.*;
import java.util.*;
import java.io.*;

import org.osm2world.core.map_data.data.MapElement;

// This class uses an input file to decide if elements are Points of Interest and, if so, which
// categories they belong to
// Singleton pattern class so we only ever have one instance
public class Categorizer {
	
	// This is the only instance of this class that can exist
	private static Categorizer instance;

        // Keeps track of how to classify elements in categories. E.g. this could have a rule 
        // saying that, to be categorized as a hospital, this element needs to have the tag "amenity=hospital" 
	private Map<String, Set<Rule>> categoryRules;

	private Categorizer() throws FileNotFoundException {
		categoryRules = new HashMap<String, Set<Rule>>();
		readInputFile();
	}

	public static Categorizer getInstance() throws FileNotFoundException {
		if (instance == null)
			instance = new Categorizer();

		return instance;
	}

	// Returns a String that represents all the categories that the element passed in belongs to
	// E.g. if the element belongs to Medical and School categories, this returns "::Medical::School"
	// Should be used as a postfix for the object name when writing an OBJ file
	// If the element does not belong to any categories, returns an empty String ""
        public String category(MapElement element) {
                String categoryString = "";

                for (String category : categoryRules.keySet()) {
                        for (Rule rule : categoryRules.get(category)) {
                                if (rule.checkElement(element)) {
                                        categoryString += "::" + category;
                                        break;
                                }
                        }
                }

                return categoryString;
        }

	public boolean isPointOfInterest(MapElement element) {
		return !category(element).isEmpty();
	}

	// Helper for the constructor. This file reads in a text file that has all of the category rules
	// written on it in a specific format. Format as follows. Unindented line is a category. Everything indented
	// under a category are the rules. There are blank lines in between each rule. A rule can be many lines,
	// each line will be "and"ed together. A category can have many rules, each rule will be "or"ed together.
	// Each rule line (or clause) contains a tag key followed by acceptable values all separated by whitespace.
	// If there are no values following the key, then it means any value is acceptable.
	// 
	// Sample file:
	// 
	// FoodAndDrink
	//        amenity bar restaurant ice_cream fast_food
	//        name
	// 
	// Tourist
	//        tourist
	// 
	//        amenity tourist travel
	//        name
	//        
	// 
	// The above file means that any element that has a name tag and amenity tags bar/restaurant/etc... is
	// categorized as FoodAndDrink, and any element that has either just a tourist tag (value does not matter)
	// or a name tag and amenity tag with value tourist/travel will be categorized at Tourist.
	private void readInputFile() throws FileNotFoundException { 
		Scanner s = new Scanner(new File("categories.txt"));
		
		String currentCategory = "";        // These variables track current category/rule getting updated
		Rule currentRule = new Rule();
		
		while (s.hasNextLine()){
		        String line = s.nextLine();
			if (line.trim().isEmpty()) {
				if (currentRule.isEmpty()) throwInputException();  // cannot add empty rule
				categoryRules.get(currentCategory).add(currentRule);
				currentRule = new Rule();
		        } else if (Character.isWhitespace(line.charAt(0))) {
		                if (currentCategory.isEmpty()) {
		                        throwInputException();  // file needs to start with a category
		                } else {
		                        Scanner l = new Scanner(line);
		                        String key = l.next();
		                        Set<String> values = new HashSet<String>();
		                        while (l.hasNext()) values.add(l.next());
		                        currentRule.addClause(key, values);
		                }
		        } else {
		                currentCategory = line.trim();
		                categoryRules.put(currentCategory, new HashSet<Rule>());
		        }
		}
        }

        // Throws an exception that tells the user the file they used as input is formatted incorrectly
        private void throwInputException() {
                throw new IllegalArgumentException("Input file (\"categories.txt\") not formatted correctly");
        }

        // This class represents a rule for categorizing map elements. A rule is made up of
        // multiple clauses which are all "and"ed together.
        private class Rule {

                // This maps from tag key to set of acceptable values
                // All clauses in this map must be met for the rule to be passed
                private Map<String, Set<String>> tags;

                public Rule() {
                        tags = new HashMap<String, Set<String>>();
                }

                // Adds a clause to the rule with the given tag key and set of acceptable values
                public void addClause(String key, Set<String> values) {
                        tags.put(key, values);
                }

                // Checks whether a map element meets this rule by examining its tags
                // If a Set of values is empty, that means any value is acceptable
                public boolean checkElement(MapElement element) {
                        for (String key : tags.keySet()) {
                                if (!element.getTags().containsKey(key))
                                        return false;
                                if (!tags.get(key).isEmpty() && !element.getTags().containsAny(key, tags.get(key)))
                                        return false;
                        }

                        return true;
                }

                public boolean isEmpty() {
                        return tags.isEmpty();
		}
	}

}


