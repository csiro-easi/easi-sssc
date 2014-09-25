package org.auscope.scm;

import org.springframework.data.annotation.Id;

import java.util.ArrayList;

public class Template {

    @Id private String id;

    private String name;
    private String description;
    private String homepage;

    private Toolbox toolbox;

    private ArrayList<Dependency> dependencies;
    private Metadata metadata;

    /**
     * @return the name
     */
    public String getName() {
        return name;
    }

    /**
     * @param name the name to set
     */
    public void setName(String name) {
        this.name = name;
    }

    /**
     * @return the description
     */
    public String getDescription() {
        return description;
    }

    /**
     * @param description the description to set
     */
    public void setDescription(String description) {
        this.description = description;
    }

    /**
     * @return the homepage
     */
    public String getHomepage() {
        return homepage;
    }

    /**
     * @param homepage the homepage to set
     */
    public void setHomepage(String homepage) {
        this.homepage = homepage;
    }

    /**
     * @return the toolbox
     */
    public Toolbox getToolbox() {
        return toolbox;
    }

    /**
     * @param toolbox the toolbox to set
     */
    public void setToolbox(Toolbox toolbox) {
        this.toolbox = toolbox;
    }

    /**
     * @return the dependencies
     */
    public ArrayList<Dependency> getDependencies() {
        return dependencies;
    }

    /**
     * @param dependencies the dependencies to set
     */
    public void setDependencies(ArrayList<Dependency> dependencies) {
        this.dependencies = dependencies;
    }

    /**
     * @return the metadata
     */
    public Metadata getMetadata() {
        return metadata;
    }

    /**
     * @param metadata the metadata to set
     */
    public void setMetadata(Metadata metadata) {
        this.metadata = metadata;
    }
}
