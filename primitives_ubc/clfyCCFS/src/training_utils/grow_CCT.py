import inspect
import scipy.io
import numpy as np
from primitives_ubc.clfyCCFS.src.utils.commonUtils import sVT
from primitives_ubc.clfyCCFS.src.utils.commonUtils import is_numeric
from primitives_ubc.clfyCCFS.src.utils.commonUtils import fastUnique
from primitives_ubc.clfyCCFS.src.utils.commonUtils import queryIfColumnsVary
from primitives_ubc.clfyCCFS.src.utils.commonUtils import queryIfOnlyTwoUniqueRows
from primitives_ubc.clfyCCFS.src.utils.ccfUtils import regCCA_alt
from primitives_ubc.clfyCCFS.src.utils.ccfUtils import random_feature_expansion
from primitives_ubc.clfyCCFS.src.utils.ccfUtils import genFeatureExpansionParameters
from primitives_ubc.clfyCCFS.src.training_utils.component_analysis import componentAnalysis
from primitives_ubc.clfyCCFS.src.training_utils.twopoint_max_marginsplit import twoPointMaxMarginSplit
import logging
logger  = logging.getLogger(__name__)

import warnings
warnings.filterwarnings('ignore')


def setupLeaf(YTrain, options):
    """
    Update tree struct to make node a leaf
    """
    tree = {}
    tree["bLeaf"]   = True
    tree["Npoints"] = YTrain.shape[0]
    tree["mean"]    = np.mean(YTrain, axis=0)

    return tree

def makeExpansionFunc(wZ, bZ, bIncOrig):
    if bIncOrig:
        f = lambda x: np.concatenate((x, random_feature_expansion(x, wZ, bZ)))
    else:
        f = lambda x: random_feature_expansion(x, wZ, bZ)

    return f


#-------------------------------------------------------------------------------
def growCCT(XTrain, YTrain, options, iFeatureNum, depth):
    """
    This function applies greedy splitting according to the CCT algorithm and the
    provided options structure. Algorithm either returns a leaf or forms an
    internal splitting node in which case the function recursively calls itself
    for each of the children, eventually returning the corresponding subtree.

    Parameters
    ----------
    XTrain      = Array giving training features.  Data should be
                  processed using processInputData before being passed to
                  CCT
    YTrain      = Output data after formatting carried out by genCCF
    options     = Options class of type optionsClassCCF.  Some fields are
                  updated during recursion
    iFeatureNum = Grouping of features as per processInputData.  During
                  recursion if a feature is found to be identical across
                  data points, the corresponding values in iFeatureNum are
                  replaced with NaNs.
    depth       = Current tree depth (zero based)


    Returns
    -------
    tree        = Structure containing learnt tree
    """
    # Standard variables
    eps = 2.2204e-16

    # Set any missing required variables
    if (options["mseTotal"]).size == 0:
        options["mseTotal"] = YTrain.var(axis=0)

    #---------------------------------------------------------------------------
    # First do checks for whether we should immediately terminate
    #---------------------------------------------------------------------------
    N = XTrain.shape[0]
    # Return if one training point, pure node or if options for returning
    # fulfilled.  A little case to deal with a binary YTrain is required.
    bStop = (N < (np.amax([2, options["minPointsForSplit"], 2 * options["minPointsLeaf"]]))) or\
            (is_numeric(options["maxDepthSplit"]) and depth > options["maxDepthSplit"])

    if depth > 490 and (options["maxDepthSplit"] == 'stack'):
        bStop = True
        logging.warning('Reached maximum depth imposed by stack limitations!')

    if bStop:
        tree = setupLeaf(YTrain, options)
        return tree

    else:
        # Check class variation
        sumY = np.sum(YTrain, axis=0)
        bYVaries = np.logical_and((sumY != 0), (sumY != N))
        if not (np.any(bYVaries)):
            tree = setupLeaf(YTrain, options)
            return tree

    #---------------------------------------------------------------------------
    # Subsample features as required for hyperplane sampling
    #---------------------------------------------------------------------------
    iCanBeSelected = fastUnique(X=iFeatureNum)
    iCanBeSelected = iCanBeSelected[~np.isnan(iCanBeSelected)]
    lambda_   = np.min((iCanBeSelected.size, options["lambda"]))
    indFeatIn = np.random.choice(int(iCanBeSelected.size), int(lambda_), replace=False)
    iFeatIn   = iCanBeSelected[indFeatIn]

    bInMat = np.equal(sVT(X=iFeatureNum.flatten(order='F')), np.sort(iFeatIn.flatten(order='F')))
    iIn = (np.any(bInMat, axis=0)).ravel().nonzero()[0]

    # Check for variation along selected dimensions and
    # resample features that have no variation
    bXVaries = queryIfColumnsVary(X=XTrain[:, iIn], tol=options["XVariationTol"])

    if (not np.all(bXVaries)):
        iInNew    = iIn
        nSelected = 0
        iIn       = iIn[bXVaries]

        while (not np.all(bXVaries)) and lambda_ > 0:
            iFeatureNum[iInNew[~bXVaries]] = np.nan
            bInMat[:, iInNew[~bXVaries]] = False
            bRemainsSelected = np.any(bInMat, axis=1)
            nSelected = nSelected + bRemainsSelected.sum(axis=0)
            iCanBeSelected = np.delete(iCanBeSelected, indFeatIn)
            lambda_   = np.min((iCanBeSelected.size, options["lambda"]-nSelected))
            if lambda_ < 1:
                break
            indFeatIn = np.random.choice(iCanBeSelected.size, size=int(lambda_), replace=False)
            iFeatIn   = iCanBeSelected[indFeatIn]
            bInMat    = np.equal(sVT(iFeatureNum.flatten(order='F')), iFeatIn.flatten(order='F'))
            iInNew    = (np.any(bInMat, axis=0)).ravel().nonzero()[0]
            bXVaries  = queryIfColumnsVary(X=XTrain[:, iInNew], tol=options["XVariationTol"])
            iIn       = np.sort(np.concatenate((iIn, iInNew[bXVaries])))

    if iIn.size == 0:
        # This means that there was no variation along any feature, therefore exit.
        tree = setupLeaf(YTrain, options)
        return tree

    #---------------------------------------------------------------------------
    # Projection bootstrap if required
    #---------------------------------------------------------------------------
    if options["bProjBoot"]:
        iTrainThis = np.random.randint(N, size=(N,1))
        XTrainBag  = XTrain[iTrainThis, iIn]
        YTrainBag  = YTrain[iTrainThis, :]
    else:
        XTrainBag = XTrain[:, iIn]
        YTrainBag = YTrain

    bXBagVaries = queryIfColumnsVary(X=XTrainBag, tol=options["XVariationTol"])

    if (not np.any(bXBagVaries)) or\
        (YTrainBag.shape[1] > 1  and (np.sum(np.absolute(np.sum(YTrainBag, axis=0)) > 1e-12) < 2)) or\
        (YTrainBag.shape[1] == 1 and (np.any(np.sum(YTrainBag, axis=0) == np.array([0, YTrainBag.shape[0]])))):
        if (not options["bContinueProjBootDegenerate"]):
            tree = setupLeaf(YTrain, options)
            return tree
        else:
            XTrainBag = XTrain[:, iIn]
            YTrainBag = YTrain

    #---------------------------------------------------------------------------
    # Check for only having two points
    #---------------------------------------------------------------------------
    if (not (len(options["projections"]) == 0)) and ((XTrainBag.shape[0] == 2) or queryIfOnlyTwoUniqueRows(X=XTrainBag)):
        bSplit, projMat, partitionPoint = twoPointMaxMarginSplit(XTrainBag, YTrainBag, options["XVariationTol"])
        if (not bSplit):
            tree = setupLeaf(YTrain, options)
            return tree
        else:
            bLessThanTrain = np.dot(XTrain[:, iIn], projMat) <= partitionPoint
            iDir = 0
    else:
        # Generate the new features as required
        if options["bRCCA"]:
            wZ, bZ  = genFeatureExpansionParameters(XTrainBag, options["rccaNFeatures"], options["rccaLengthScale"])
            fExp    = makeExpansionFunc(wZ, bZ, options["rccaIncludeOriginal"])
            projMat, _, _ = regCCA_alt(XTrainBag, YTrainBag, options["rccaRegLambda"], options["rccaRegLambda"], 1e-8)
            if projMat.size == 0:
                projMat = np.ones((XTrainBag.shape[1], 1))
            UTrain = np.dot(fExp(XTrain[:, iIn]), projMat)

        else:
            projMat, yprojMat, _, _, _ = componentAnalysis(XTrainBag, YTrainBag, options["projections"], options["epsilonCCA"])
            UTrain = np.dot(XTrain[:, iIn], projMat)

        #-----------------------------------------------------------------------
        # Choose the features to use
        #-----------------------------------------------------------------------
        # This step catches splits based on no significant variation
        bUTrainVaries = queryIfColumnsVary(UTrain, options["XVariationTol"])

        if (not np.any(bUTrainVaries)):
            tree = setupLeaf(YTrain, options)
            return tree

        UTrain  = UTrain[:, bUTrainVaries]
        projMat = projMat[:, bUTrainVaries]

        #-----------------------------------------------------------------------
        # Search over splits using provided method
        #-----------------------------------------------------------------------
        nProjDirs  = UTrain.shape[1]
        splitGains = np.empty((nProjDirs,1))
        splitGains.fill(np.nan)
        iSplits    = np.empty((nProjDirs,1))
        iSplits.fill(np.nan)

        for nVarAtt in range(nProjDirs):
            # Calculate the probabilities of being at each class in each of child
            # nodes based on proportion of training data for each of possible
            # splits using current projection
            sort_UTrain   = UTrain[:, nVarAtt].flatten(order='F')
            UTrainSort    = np.sort(sort_UTrain)
            iUTrainSort   = np.argsort(sort_UTrain)
            bUniquePoints = np.concatenate((np.diff(UTrainSort, n=1, axis=0) > options["XVariationTol"], np.array([False])))

            VTrainSort = YTrain[iUTrainSort, :]

            leftCum = np.cumsum(VTrainSort, axis=0)
            if (YTrain.shape[1] ==1 or options["bSepPred"]):
                # Convert to [class_doesnt_exist,class_exists]
                leftCum = np.concatenate((np.subtract(sVT(X=np.arange(0,N)), leftCum), leftCum))

            rightCum = np.subtract(leftCum[-1, :], leftCum)

            # Calculate the metric values of the current node and two child nodes
            pL = np.divide(leftCum,  (np.arange(1, N+1)[np.newaxis]).T)
            pR = np.divide(rightCum, (np.arange(N-1, -1, -1)[np.newaxis]).T)

            split_criterion = options["splitCriterion"]
            if split_criterion == 'gini':
                # Can ignore the 1 as this cancels in the gain
                lTerm = -pL**2
                rTerm = -pR**2
            elif split_criterion =='info':
                lTerm = np.multiply(-pL, np.log2(pL))
                lTerm[np.absolute(pL) == 0] = 0
                rTerm = np.multiply(-pR, np.log2(pR))
                rTerm[np.absolute(pR) == 0] = 0
            else:
                assert (False), 'Invalid split criterion!'

            if (YTrain.shape[1] == 1) or options["bSepPred"]:
                # Add grouped terms back together
                end   = YTrain.shape[1]
                lTerm = np.add(lTerm[:, 0:end//2], lTerm[:, end//2:])
                rTerm = np.add(rTerm[:, 0:end//2], rTerm[:, end//2:])

            if (not is_numeric(options["taskWeights"])) and (not options["multiTaskGainCombination"] == 'max'):
                # No need to do anything fancy in the metric calculation
                metricLeft  = np.sum(lTerm, axis=1)
                metricRight = np.sum(rTerm, axis=1)
            else:
                # Need to do grouped sums for each of the outputs as will be
                # doing more than a simple averaging of there values
               metricLeft = np.cumsum(lTerm, axis=1)
               taskidxs_L = np.array([(options["task_ids"][1:] - 1), np.array([-1])])
               metricLeft = metricLeft[:, taskidxs_L] - np.concatenate((np.zeros((metricLeft.shape[0], 1)), metricLeft[:, (options["task_ids"][1:] - 1)]))

               metricRight = np.cumsum(rTerm, axis=1)
               taskidxs_R  = np.array([(options["task_ids"][1:] - 1), np.array([-1])])
               metricRight = metricRight[:, taskidxs_R] - np.concatenate((np.zeros((metricRight.shape[0], 1)), metricRight[:, (options["task_ids"][1:] - 1)]))

            metricCurrent = np.copy(metricLeft[-1])
            metricLeft[~bUniquePoints]  = np.inf
            metricRight[~bUniquePoints] = np.inf
            # Calculate gain in metric for each of possible splits based on current
            # metric value minus metric value of child weighted by number of terms
            # in each child
            metricGain = np.subtract(metricCurrent,\
                  np.add(np.multiply(np.arange(1,N+1, 1), metricLeft),\
                         np.multiply(np.arange(N-1, -1, -1), metricRight))/N)

            # Combine gains if there are mulitple outputs.  Note that for gini,
            # info and mse, the joint gain is equal to the mean gain, hence
            # taking the mean here rather than explicitly calculating joints before.
            if len(metricGain.shape) > 1:
                if metricGain.shape[1] > 1:
                    if is_numeric(options["taskWeights"]):
                        # If weights provided, weight task appropriately in terms of importance.
                        metricGain = np.multiply(metricGain, X=sVT(options["taskWeights"].flatten(order='F')))

                    multiTGC = options["multiTaskGainCombination"]
                    if multiTGC == 'mean':
                        metricGain = np.mean(metricGain, axis=1)
                    elif multiTGC == 'max':
                        metricGain = np.max(metricGain, axis=1)
                    else:
                        assert (False), 'Invalid option for options.multiTaskGainCombination!'

            # Disallow splits that violate the minimum number of leaf points
            end = (metricGain.shape[0]-1)
            metricGain[0:(options["minPointsLeaf"]-1)] = -np.inf
            metricGain[(end-(options["minPointsLeaf"]-1)):] = -np.inf # Note that end is never chosen anyway

            # Randomly sample from equally best splits
            iSplits[nVarAtt]    = np.argmax(metricGain[0:-1])
            splitGains[nVarAtt] = np.max(metricGain[0:-1])
            iEqualMax = ((np.absolute(metricGain[0:-1] - splitGains[nVarAtt]) < (10*eps)).ravel().nonzero())[0]
            if iEqualMax.size == 0:
                iEqualMax = np.array([1])
            iSplits[nVarAtt] = iEqualMax[np.random.randint(iEqualMax.size)]

        # If no split gives a positive gain then stop
        if np.max(splitGains) < 0:
            tree = setupLeaf(YTrain, options)
            return tree

        # Establish between projection direction
        maxGain   = np.max(splitGains, axis=0)
        iEqualMax = ((np.absolute(splitGains - maxGain) < (10 * eps)).ravel().nonzero())[0]

        # Use given method to break ties
        if options["dirIfEqual"] == 'rand':
            iDir = iEqualMax[np.random.randint(iEqualMax.size)]
        elif options["dirIfEqual"] == 'first':
            if iEqualMax.size == 0:
                iDir = 0
            else:
                iDir = iEqualMax[0]
        else:
            assert (False), 'invalid dirIfEqual!'
        iSplit = iSplits[iDir].astype(int)

        #-----------------------------------------------------------------------
        # Establish partition point and assign to child
        #-----------------------------------------------------------------------
        UTrain = UTrain[:, iDir]
        UTrainSort = np.sort(UTrain)

        # The convoluted nature of the below is to avoid numerical errors
        uTrainSortLeftPart = UTrainSort[iSplit]
        UTrainSort     = UTrainSort - uTrainSortLeftPart
        partitionPoint = UTrainSort[iSplit]*0.5 + UTrainSort[iSplit+1]*0.5
        partitionPoint = partitionPoint + uTrainSortLeftPart
        UTrainSort     = UTrainSort + uTrainSortLeftPart

        bLessThanTrain = (UTrain <= partitionPoint)

        if (not np.any(bLessThanTrain)) or np.all(bLessThanTrain):
            assert (False), 'Suggested split with empty!'

    #-----------------------------------------------------------------------
    # Recur tree growth to child nodes and constructs tree struct
    #-----------------------------------------------------------------------
    tree = {}
    tree["bLeaf"]   = False
    tree["Npoints"] = N
    tree["mean"]    = np.mean(YTrain, axis=0)

    bLessThanTrain = np.squeeze(bLessThanTrain)
    treeLeft  = growCCT(XTrain[bLessThanTrain, :], YTrain[bLessThanTrain,  :], options, iFeatureNum, depth+1)
    treeRight = growCCT(XTrain[~bLessThanTrain,:], YTrain[~bLessThanTrain, :], options, iFeatureNum, depth+1)
    tree["iIn"] = iIn

    if options["bRCCA"]:
        try:
            if inspect.isfunction(fExp):
                tree["featureExpansion"] = fExp # Ensure variable is defined
        except NameError:
            pass

    if len(projMat.shape) < 2:
        projMat = np.expand_dims(projMat, axis=1)

    tree["decisionProjection"] = projMat[:, iDir]
    tree["paritionPoint"]      = partitionPoint
    tree["lessthanChild"]      = treeLeft
    tree["greaterthanChild"]   = treeRight

    return tree