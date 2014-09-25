package org.auscope.scm;

import java.util.List;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.repository.query.Param;
import org.springframework.data.rest.core.annotation.RepositoryRestResource;

@RepositoryRestResource(collectionResourceRel = "toolboxes", path = "toolboxes")
public interface ToolboxRepository extends MongoRepository<Toolbox, String> {

    List<Toolbox> findByName(@Param("name") String name);

}
