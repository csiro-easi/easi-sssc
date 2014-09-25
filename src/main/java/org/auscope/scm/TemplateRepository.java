package org.auscope.scm;

import java.util.List;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.repository.query.Param;
import org.springframework.data.rest.core.annotation.RepositoryRestResource;

@RepositoryRestResource(collectionResourceRel = "templates", path = "templates")
public interface TemplateRepository extends MongoRepository<Template, String> {

    List<Template> findByName(@Param("name") String name);

}
