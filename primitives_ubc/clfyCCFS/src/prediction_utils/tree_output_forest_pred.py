import numpy as np
from sklearn.preprocessing import OneHotEncoder
from primitives_ubc.clfyCCFS.src.utils.commonUtils import is_numeric
from primitives_ubc.clfyCCFS.src.utils.commonUtils import islogical


def treeOutputsToForestPredicts(CCF, treeOutputs):
    """
    Converts outputs from individual trees to forest predctions and
    probabilities.

    Parameters
    ----------
    CCF = Output of genCCF
    treeOutputs = Array typically generated by predictCCF. Description provided
                  in doc string of predictCCF as it is provided as an output.
    """
    forestProbs = np.squeeze(np.mean(treeOutputs, axis=1))

    if CCF["options"]["bSepPred"]:
        forestPredicts = forestProbs > 0.5

    else:
        if isinstance(CCF["classNames"], type(OneHotEncoder(handle_unknown='ignore'))):
            enc = CCF["classNames"]
            # Check if task_ids is single number
            if type(CCF["options"]["task_ids"]) == int:
                if CCF["options"]["task_ids"] == 1:
                    task_ids_size  = 1
                    forestPredicts = np.empty((forestProbs.shape[0], task_ids_size))
                    forestPredicts.fill(np.nan)
                    forestPredicts[:, 0] = np.argmax(forestProbs, axis=1)
                else:
                    assert (CCF["options"]["task_ids"] == 1), 'Task size is not one or not given in array!'
            else:
                if (CCF["options"]["task_ids"]).size == 1:
                    task_ids_size  = 1
                    forestPredicts = np.empty((forestProbs.shape[0], task_ids_size))
                    forestPredicts.fill(np.nan)
                    forestPredicts[:, 0] = np.argmax(forestProbs, axis=1)
                else:
                    forestPredicts = np.empty((forestProbs.shape[0], CCF["options"]["task_ids"].size))
                    forestPredicts.fill(np.nan)
                    for nO in range((CCF["options"]["task_ids"].size)-1):
                        forestPredicts[:, nO] = np.argmax(forestProbs[:, CCF["options"]["task_ids"][nO]:(CCF["options"]["task_ids"][nO+1]-1)], axis=1)
                    forestPredicts[:, -1] = np.argmax(forestProbs[:, CCF["options"]["task_ids"][-1]:], axis=1)
            # Convert to one-hot encoding
            nCats = len(enc.categories_[0])
            forestPredicts1 = np.zeros((forestPredicts.shape[0], nCats))
            for idx in range(forestPredicts.shape[0]):
                forestPredicts1[idx, int(forestPredicts[idx, 0])] = 1
            # Convert from categorical to labels
            forestPredicts = enc.inverse_transform(forestPredicts1)

        else:
            # Check if task_ids is single number
            if type(CCF["options"]["task_ids"]) == int:
                if CCF["options"]["task_ids"] == 1:
                    task_ids_size  = 1
                    forestPredicts = np.empty((forestProbs.shape[0], task_ids_size))
                    forestPredicts.fill(np.nan)
                    forestPredicts[:, 0] = np.argmax(forestProbs, axis=1)
                else:
                    assert (CCF["options"]["task_ids"] == 1), 'Task size is not one or not given in array!'
            else:
                if (CCF["options"]["task_ids"]).size == 1:
                    task_ids_size  = 1
                    forestPredicts = np.empty((forestProbs.shape[0], task_ids_size))
                    forestPredicts.fill(np.nan)
                    forestPredicts[:, 0] = np.argmax(forestProbs, axis=1)
                else:
                    forestPredicts = np.empty((forestProbs.shape[0], CCF["options"]["task_ids"].size))
                    forestPredicts.fill(np.nan)
                    for nO in range((CCF["options"]["task_ids"].size)-1):
                        forestPredicts[:, nO] = np.argmax(forestProbs[:, CCF["options"]["task_ids"][nO]:(CCF["options"]["task_ids"][nO+1]-1)], axis=1)
                    forestPredicts[:, -1] = np.argmax(forestProbs[:, CCF["options"]["task_ids"][-1]:], axis=1)
            # Convert to type int
            forestPredicts = forestPredicts.astype(int)

            if is_numeric(CCF["classNames"]):
                if islogical(forestPredicts):
                    assert (forestPredicts.shape[1] == 1), 'Class names should have been a cell if multiple outputs!'
                    forestPredicts = CCF["classNames"][forestPredicts+1]
                else:
                    forestPredicts = CCF["classNames"][forestPredicts]

            elif isinstance(CCF["classNames"], type(np.array([]))):
                forestPredicts = CCF["classNames"][forestPredicts]

            elif islogical(CCF["classNames"]) and CCF["classNames"].size:
                forestPredicts = (forestPredicts == 2)


    return forestPredicts, forestProbs
