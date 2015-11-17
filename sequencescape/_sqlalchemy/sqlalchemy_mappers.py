from typing import Union, List, Any, Tuple

from sqlalchemy import Column

from sequencescape.enums import Property
from sequencescape.mappers import Mapper, LibraryMapper, MultiplexedLibraryMapper, SampleMapper, WellMapper, StudyMapper
from sequencescape.models import Model, Library, MultiplexedLibrary, Sample, Well, Study
from sequencescape._sqlalchemy.sqlalchemy_model_converters import convert_to_sqlalchemy_model, convert_to_popo_models,\
    get_equivalent_sqlalchemy_model_type
from sequencescape._sqlalchemy.sqlalchemy_database_connector import SQLAlchemyDatabaseConnector
from sequencescape._sqlalchemy.sqlalchemy_models import SQLAlchemyModel, SQLAlchemyStudySamplesLink, SQLAlchemyIsCurrentModel


class SQLAlchemyMapper(Mapper):
    def __init__(self, database_connector: SQLAlchemyDatabaseConnector, model_type: type):
        """
        Default constructor.
        :param database_connector: the object through which database connections can be made
        :param model_type: the type of the model that the mapper is used for
        """
        if not model_type:
            raise ValueError("Model type must be specified through `model_type` parameter")
        if not issubclass(model_type, Model):
            raise ValueError("Model type (%s) must be a subclass of `Model`" % model_type)

        self._database_connector = database_connector
        self._model_type = model_type
        self._sqlalchemy_model_type = get_equivalent_sqlalchemy_model_type(self._model_type)

        if self._sqlalchemy_model_type is None:
            raise NotImplementedError("Not implemented for models of type: `%s`" % model_type)

    def add(self, models: Union[Model, List[Model]]):
        if models is None:
            # TODO: Generalise to anything that's not a subclass of model
            raise ValueError("Cannot add `None`")
        if not isinstance(models, list):
            models = [models]

        session = self._database_connector.create_session()
        for model in models:
            sqlalchemy_model = convert_to_sqlalchemy_model(model)
            session.add(sqlalchemy_model)
        session.commit()
        session.close()

    def get_all(self) -> List[Model]:
        query_model = self._sqlalchemy_model_type
        session = self._database_connector.create_session()
        result = session.query(query_model). \
            filter(query_model.is_current).all()
        session.close()
        assert isinstance(result, list)
        return convert_to_popo_models(result)

    def _get_by_property_value_list(self, property: Property, required_property_values: List[Any]) -> List[Model]:
        # FIXME: Should this always limit `is_current` to 1 - model might not even have this property!
        if not issubclass(self._sqlalchemy_model_type, SQLAlchemyIsCurrentModel):
            raise ValueError(
                "Not possible to get instances of type %s by name as the query required `is_current` property"
                    % self._model_type)

        if len(required_property_values) == 0:
            return []

        query_model = self._sqlalchemy_model_type
        session = self._database_connector.create_session()

        # FIXME: It is an assumption that the Model property has the same name as SQLAlchemyModel
        query_column = query_model.__dict__[property]   # type: Column
        result = session.query(query_model). \
            filter(query_column.in_(required_property_values)). \
            filter(query_model.is_current).all()
        session.close()
        assert isinstance(result, list)
        return convert_to_popo_models(result)


class SQLAlchemySampleMapper(SQLAlchemyMapper, SampleMapper):
    def __init__(self, database_connector: SQLAlchemyDatabaseConnector):
        """
        Default constructor.
        :param database_connector: the database connector
        """
        super(SQLAlchemySampleMapper, self).__init__(database_connector, Sample)

    def get_associated_with_study(self, study_ids: Union[Study, List[Study]]) -> List[Sample]:
        if not isinstance(study_ids, list):
            study_ids = [study_ids]

        # FIXME: This implementation is bad - would be better to sort SQLAlchemy models to do the link correctly
        session = self._database_connector.create_session()

        studies_samples = session.query(SQLAlchemyStudySamplesLink). \
            filter(SQLAlchemyStudySamplesLink.study_internal_id.in_(study_ids)). \
            filter(SQLAlchemyStudySamplesLink.is_current).all()

        if not studies_samples:
            return []

        sample_ids = [study_sample.sample_internal_id for study_sample in studies_samples]
        return self.get_by_id(sample_ids)


class SQLAlchemyStudyMapper(SQLAlchemyMapper, StudyMapper):
    def __init__(self, database_connector: SQLAlchemyDatabaseConnector):
        """
        Default constructor.
        :param database_connector: the database connector
        """
        super(SQLAlchemyStudyMapper, self).__init__(database_connector, Study)

    def get_associated_with_sample(self, sample_ids: Union[Sample, List[Sample]]) -> List[Study]:
        if not isinstance(sample_ids, list):
            sample_ids = [sample_ids]

        # FIXME: This implementation is bad - would be better to sort SQLAlchemy models to do the link correctly
        session = self._database_connector.create_session()

        studies_samples = session.query(SQLAlchemyStudySamplesLink). \
            filter(SQLAlchemyStudySamplesLink.sample_internal_id.in_(sample_ids)). \
            filter(SQLAlchemyStudySamplesLink.is_current).all()

        if not studies_samples:
            return []

        study_ids = [study_sample.study_internal_id for study_sample in studies_samples]
        return self.get_by_id(study_ids)


class SQLAlchemyLibraryMapper(SQLAlchemyMapper, LibraryMapper):
    def __init__(self, database_connector: SQLAlchemyDatabaseConnector):
        """
        Default constructor.
        :param database_connector: the database connector
        """
        super(SQLAlchemyLibraryMapper, self).__init__(database_connector, Library)


class SQLAlchemyWellMapper(SQLAlchemyMapper, WellMapper):
    def __init__(self, database_connector: SQLAlchemyDatabaseConnector):
        """
        Default constructor.
        :param database_connector: the database connector
        """
        super(SQLAlchemyWellMapper, self).__init__(database_connector, Well)


class SQLAlchemyMultiplexedLibraryMapper(SQLAlchemyMapper, MultiplexedLibraryMapper):
    def __init__(self, database_connector: SQLAlchemyDatabaseConnector):
        """
        Default constructor.
        :param database_connector: the database connector
        """
        super(SQLAlchemyMultiplexedLibraryMapper, self).__init__(database_connector, MultiplexedLibrary)
