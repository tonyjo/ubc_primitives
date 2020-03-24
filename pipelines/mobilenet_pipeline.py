import argparse

from d3m import index
from d3m.metadata import base as metadata_base
from d3m.metadata.base import Context, ArgumentType
from d3m.metadata.pipeline import Pipeline, PrimitiveStep

# Common Primitives
from common_primitives import construct_predictions
from common_primitives.denormalize import DenormalizePrimitive
from common_primitives.column_parser import ColumnParserPrimitive
from common_primitives.dataset_to_dataframe import DatasetToDataFramePrimitive
from common_primitives.xgboost_regressor import XGBoostGBTreeRegressorPrimitive
from common_primitives.extract_columns_semantic_types import ExtractColumnsBySemanticTypesPrimitive

# Testing Primitive
from primitives.mobilenet.mobnetcnn import MobileNetCNN


def make_pipeline_1():
    pipeline = Pipeline()
    pipeline.add_input(name='inputs')

    # Step 0: Denormalize
    step_0 = PrimitiveStep(primitive_description=DenormalizePrimitive.metadata.query())
    step_0.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='inputs.0')
    step_0.add_output('produce')
    pipeline.add_step(step_0)

    # Step 1: DatasetToDataFrame
    step_1 = PrimitiveStep(primitive_description=DatasetToDataFramePrimitive.metadata.query())
    step_1.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.0.produce')
    step_1.add_output('produce')
    pipeline.add_step(step_1)

    # Step 2: Feature Extraction Primitive
    step_2 = PrimitiveStep(primitive=MobileNetCNN)
    step_2.add_hyperparameter(name='feature_extract_only', argument_type=ArgumentType.VALUE, data=True)
    step_2.add_hyperparameter(name='include_top', argument_type=ArgumentType.VALUE, data=False)
    step_2.add_argument(name='inputs',  argument_type=ArgumentType.CONTAINER, data_reference='steps.1.produce')
    step_2.add_argument(name='outputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.1.produce')
    step_2.add_output('produce')
    pipeline.add_step(step_2)

    # Step 3: Column Parser
    step_3 = PrimitiveStep(primitive_description=ColumnParserPrimitive.metadata.query())
    step_3.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.2.produce')
    step_3.add_output('produce')
    pipeline.add_step(step_3)

    # Step 4: Extract Attributes
    step_4 = PrimitiveStep(primitive_description=ExtractColumnsBySemanticTypesPrimitive.metadata.query())
    step_4.add_hyperparameter(name='semantic_types', argument_type=ArgumentType.VALUE, data=['https://metadata.datadrivendiscovery.org/types/Attribute'])
    step_4.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.3.produce')
    step_4.add_output('produce')
    pipeline.add_step(step_4)

    # Step 5: Extract Targets
    step_5 = PrimitiveStep(primitive_description=ExtractColumnsBySemanticTypesPrimitive.metadata.query())
    step_5.add_hyperparameter(name='semantic_types', argument_type=ArgumentType.VALUE, data=['https://metadata.datadrivendiscovery.org/types/SuggestedTarget'])
    step_5.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.1.produce')
    step_5.add_output('produce')
    pipeline.add_step(step_5)

    attributes = 'steps.4.produce'
    targets    = 'steps.5.produce'

    # Step 6: XGB
    step_6 = PrimitiveStep(primitive=XGBoostGBTreeRegressorPrimitive)
    step_6.add_argument(name='inputs',  argument_type=ArgumentType.CONTAINER, data_reference=attributes)
    step_6.add_argument(name='outputs', argument_type=ArgumentType.CONTAINER, data_reference=targets)
    step_6.add_output('produce')
    pipeline.add_step(step_6)

    # step 7: Construct output
    step_7 = PrimitiveStep(primitive=index.get_primitive('d3m.primitives.data_transformation.construct_predictions.Common'))
    step_7.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.6.produce')
    step_7.add_argument(name='reference', argument_type=ArgumentType.CONTAINER, data_reference='steps.1.produce')
    step_7.add_output('produce')
    pipeline.add_step(step_7)

    # Final Output
    pipeline.add_output(name='output predictions', data_reference='steps.7.produce')

    # print(pipeline.to_json())

    with open('./mobnet_pipeline_1.json', 'w') as write_file:
        write_file.write(pipeline.to_json(indent=4, sort_keys=False, ensure_ascii=False))

    print('Generated pipeline - 1!')

def make_pipeline_2():
    pipeline = Pipeline()
    pipeline.add_input(name='inputs')

    # Step 0: Denormalize
    step_0 = PrimitiveStep(primitive_description=DenormalizePrimitive.metadata.query())
    step_0.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='inputs.0')
    step_0.add_output('produce')
    pipeline.add_step(step_0)

    # Step 1: DatasetToDataFrame
    step_1 = PrimitiveStep(primitive_description=DatasetToDataFramePrimitive.metadata.query())
    step_1.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.0.produce')
    step_1.add_output('produce')
    pipeline.add_step(step_1)

    # Step 2: Column Parser
    step_2 = PrimitiveStep(primitive_description=ColumnParserPrimitive.metadata.query())
    step_2.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.1.produce')
    step_2.add_output('produce')
    pipeline.add_step(step_2)

    # Step 3: Extract Attributes
    step_3 = PrimitiveStep(primitive_description=ExtractColumnsBySemanticTypesPrimitive.metadata.query())
    step_3.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.2.produce')
    step_3.add_hyperparameter(name='semantic_types', argument_type=ArgumentType.VALUE, data=['https://metadata.datadrivendiscovery.org/types/Attribute'])
    step_3.add_output('produce')
    pipeline.add_step(step_3)

    # Step 4: Extract Targets
    step_4 = PrimitiveStep(primitive_description=ExtractColumnsBySemanticTypesPrimitive.metadata.query())
    step_4.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.1.produce')
    step_4.add_hyperparameter(name='semantic_types', argument_type=ArgumentType.VALUE, data=['https://metadata.datadrivendiscovery.org/types/SuggestedTarget'])
    step_4.add_output('produce')
    pipeline.add_step(step_4)

    attributes = 'steps.1.produce'
    targets    = 'steps.4.produce'

    # Step 5: Feature Extraction and Fit Primitive
    step_5 = PrimitiveStep(primitive=MobileNetCNN)
    step_5.add_hyperparameter(name='output_dim', argument_type=ArgumentType.VALUE, data=1)
    step_5.add_hyperparameter(name='num_iterations', argument_type=ArgumentType.VALUE, data=100)
    step_5.add_hyperparameter(name='feature_extract_only', argument_type=ArgumentType.VALUE, data=False)
    step_5.add_argument(name='inputs',  argument_type=ArgumentType.CONTAINER, data_reference=attributes)
    step_5.add_argument(name='outputs', argument_type=ArgumentType.CONTAINER, data_reference=targets)
    step_5.add_output('produce')
    pipeline.add_step(step_5)

    # step 6: construct output
    step_6 = PrimitiveStep(primitive=index.get_primitive('d3m.primitives.data_transformation.construct_predictions.Common'))
    step_6.add_argument(name='inputs',    argument_type=ArgumentType.CONTAINER, data_reference='steps.5.produce')
    step_6.add_argument(name='reference', argument_type=ArgumentType.CONTAINER, data_reference='steps.1.produce')
    step_6.add_output('produce')
    pipeline.add_step(step_6)

    # Final Output
    pipeline.add_output(name='output predictions', data_reference='steps.6.produce')

    # print(pipeline.to_json())

    with open('./mobnet_pipeline_2.json', 'w') as write_file:
        write_file.write(pipeline.to_json(indent=4, sort_keys=False, ensure_ascii=False))

    print('Generated pipeline - 2!')


def main(select_pipeline):
    if select_pipeline == 1:
        make_pipeline_1()
    else:
        make_pipeline_2()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Genereate GoogleNet based pipeline.')
    parser.add_argument('-s', action='store', dest='select_pipeline', type=int, help='Which pipeline to generate')
    args = parser.parse_args()

    # Generate pipeline for Hand geometry dataset
    main(select_pipeline=args.select_pipeline)