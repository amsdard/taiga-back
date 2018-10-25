# -*- coding: utf-8 -*-
# Copyright (C) 2014-2017 Andrey Antukh <niwi@niwi.nz>
# Copyright (C) 2014-2017 Jesús Espino <jespinog@gmail.com>
# Copyright (C) 2014-2017 David Barragán <bameda@dbarragan.com>
# Copyright (C) 2014-2017 Alejandro Alonso <alejandro.alonso@kaleidos.net>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from django.utils.translation import ugettext_lazy as _

from taiga.base.fields import JSONField
from taiga.base.exceptions import ValidationError
from taiga.base.api.validators import ModelValidator
from taiga.projects.custom_attributes.models import UserStoryCustomAttribute


from . import models
import re

######################################################
# Custom Attribute Validator
#######################################################

class BaseCustomAttributeValidator(ModelValidator):
    class Meta:
        read_only_fields = ('id',)
        exclude = ('created_date', 'modified_date')

    def _validate_integrity_between_project_and_name(self, attrs, source):
        """
        Check the name is not duplicated in the project. Check when:
          - create a new one
          - update the name
          - update the project (move to another project)
        """
        data_id = attrs.get("id", None)
        data_name = attrs.get("name", None)
        data_project = attrs.get("project", None)

        if self.object:
            data_id = data_id or self.object.id
            data_name = data_name or self.object.name
            data_project = data_project or self.object.project

        model = self.Meta.model
        qs = (model.objects.filter(project=data_project, name=data_name)
                           .exclude(id=data_id))
        if qs.exists():
            raise ValidationError(_("Already exists one with the same name."))

        return attrs

    def validate_name(self, attrs, source):
        return self._validate_integrity_between_project_and_name(attrs, source)

    def validate_project(self, attrs, source):
        return self._validate_integrity_between_project_and_name(attrs, source)


class EpicCustomAttributeValidator(BaseCustomAttributeValidator):
    class Meta(BaseCustomAttributeValidator.Meta):
        model = models.EpicCustomAttribute


class UserStoryCustomAttributeValidator(BaseCustomAttributeValidator):
    class Meta(BaseCustomAttributeValidator.Meta):
        model = models.UserStoryCustomAttribute


class TaskCustomAttributeValidator(BaseCustomAttributeValidator):
    class Meta(BaseCustomAttributeValidator.Meta):
        model = models.TaskCustomAttribute


class IssueCustomAttributeValidator(BaseCustomAttributeValidator):
    class Meta(BaseCustomAttributeValidator.Meta):
        model = models.IssueCustomAttribute


######################################################
# Custom Attribute Validator
#######################################################


class BaseCustomAttributesValuesValidator(ModelValidator):
    attributes_values = JSONField(source="attributes_values", label="attributes values")
    _custom_attribute_model = None
    _container_field = None

    class Meta:
        exclude = ("id",)

    @staticmethod
    def validate_estimation(value):
        regular_expression = '([0-9]+w)*([0-9]+d)*([0-9]+h)*'
        timestamps = [int('0' + item[:-1]) for item in re.findall(regular_expression, value)[0]]
        while timestamps[2] >= 8:
            timestamps[2] -= 8
            timestamps[1] += 1
        while timestamps[1] >= 5:
            timestamps[1] -= 5
            timestamps[0] += 1
        timestamps[0] = str(timestamps[0]) + 'w' if timestamps[0] > 0 else ''
        timestamps[1] = str(timestamps[1]) + 'd' if timestamps[1] > 0 else ''
        timestamps[2] = str(timestamps[2]) + 'h' if timestamps[2] > 0 else ''
        return ''.join(timestamps)

    def validate_attributes_values(self, attrs, source):
        estimate_field_ids = [field.id for field in UserStoryCustomAttribute.objects.all() if field.type == "est"]
        attributes_dict = attrs['attributes_values']
        for key in attributes_dict:
            if int(key) in estimate_field_ids:
                attributes_dict[key] = self.validate_estimation(attributes_dict[key])
        # values must be a dict
        data_values = attrs.get("attributes_values", None)
        if self.object:
            data_values = (data_values or self.object.attributes_values)

        if type(data_values) is not dict:
            raise ValidationError(_("Invalid content. It must be {\"key\": \"value\",...}"))

        # Values keys must be in the container object project
        data_container = attrs.get(self._container_field, None)
        if data_container:
            project_id = data_container.project_id
        elif self.object:
            project_id = getattr(self.object, self._container_field).project_id
        else:
            project_id = None

        values_ids = list(data_values.keys())
        qs = self._custom_attribute_model.objects.filter(project=project_id,
                                                         id__in=values_ids)
        if qs.count() != len(values_ids):
            raise ValidationError(_("It contain invalid custom fields."))

        return attrs


class EpicCustomAttributesValuesValidator(BaseCustomAttributesValuesValidator):
    _custom_attribute_model = models.EpicCustomAttribute
    _container_model = "epics.Epic"
    _container_field = "epic"

    class Meta(BaseCustomAttributesValuesValidator.Meta):
        model = models.EpicCustomAttributesValues


class UserStoryCustomAttributesValuesValidator(BaseCustomAttributesValuesValidator):
    _custom_attribute_model = models.UserStoryCustomAttribute
    _container_model = "userstories.UserStory"
    _container_field = "user_story"

    class Meta(BaseCustomAttributesValuesValidator.Meta):
        model = models.UserStoryCustomAttributesValues


class TaskCustomAttributesValuesValidator(BaseCustomAttributesValuesValidator, ModelValidator):
    _custom_attribute_model = models.TaskCustomAttribute
    _container_field = "task"

    class Meta(BaseCustomAttributesValuesValidator.Meta):
        model = models.TaskCustomAttributesValues


class IssueCustomAttributesValuesValidator(BaseCustomAttributesValuesValidator, ModelValidator):
    _custom_attribute_model = models.IssueCustomAttribute
    _container_field = "issue"

    class Meta(BaseCustomAttributesValuesValidator.Meta):
        model = models.IssueCustomAttributesValues
