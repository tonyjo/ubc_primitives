import subprocess
from setuptools import setup, find_packages

# Run
subprocess.run(["apt", "update"])
subprocess.run(["apt", "install", "python3.6-gdbm"])

# Get install requirements
with open('requirements.txt', 'r') as f:
    install_requires = list()
    dependency_links = list()
    for line in f:
        re = line.strip()
        if re:
            install_requires.append(re)

setup(name='ubc_primitives',
      version='0.1.0',
      description='Setup primitive build model paths',
      author='UBC',
      url='https://github.com/plai-group/ubc_primitives.git',
      maintainer_email='tonyjos@cs.ubc.ca',
      maintainer='Tony Joseph',
      license='Apache-2.0',
      packages=find_packages(exclude=['pipelines']),
      zip_safe=False,
      python_requires='>=3.6',
      install_requires=install_requires,
      keywords='d3m_primitive',
      entry_points={
          'd3m.primitives': [
              'schema_discovery.profiler.UBC=primitives.smi:SemanticTypeInfer',
              'feature_extraction.bag_of_characters.UBC=primitives.boc:BagOfCharacters',
              'feature_extraction.bag_of_words.UBC=primitives.bow:BagOfWords',
              'feature_extraction.cnn.UBC=primitives.cnn:ConvolutionalNeuralNetwork',
              'feature_extraction.googlenet.UBC=primitives.googlenet:GoogleNetCNN',
              'feature_extraction.mobilenet.UBC=primitives.mobilenet:MobileNetCNN',
              'feature_extraction.resnet.UBC=primitives.resnet:ResNetCNN',
              'feature_extraction.vggnet.UBC=primitives.vgg:VGG16CNN',
              'classification.ccfs.UBC=primitives.clfyCCFS:CanonicalCorrelationForestsClassifierPrimitive',
              'regression.ccfs.UBC=primitives.regCCFS:CanonicalCorrelationForestsRegressionPrimitive',
              'classification.mlp.UBC=primitives.clfyMLP:MultilayerPerceptronClassifierPrimitive',
              'regression.mlp.UBC=primitives.regMLP:MultilayerPerceptronRegressionPrimitive',
              'clustering.kmeans.UBC=primitives.kmeans:KMeansClusteringPrimitive',
              'dimensionality_reduction.pca.UBC=primitives.pca:PrincipalComponentAnalysisPrimitive',
              'classification.simpleCnaps.UBC=primitives.simpleCNAPS:SimpleCNAPSClassifierPrimitive',
              'regression.LinearRegression.UBC=primitives.linearRegression:LinearRegressionPrimitive',
              'classification.LogisticRegression.UBC=primitives.logisticRegression:LogisticRegressionPrimitive',
              'operator.DiagonalMVN.UBC=primitives.diagonalMVN:DiagonalMVNPrimitive',
          ],
      })

