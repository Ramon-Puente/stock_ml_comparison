# -*- coding: utf-8 -*-
"""fproj_2

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1D7MIjrBUgJYSitb7LM_Ab5W5qDg6cumZ

## **Importing Packages**
"""



# Commented out IPython magic to ensure Python compatibility.
# %matplotlib inline
import pandas as pd
import numpy as np
import seaborn as sns
# import plotly.express as px
# import plotly.graph_objects as go
import matplotlib.pyplot as plt


# Scikit-learn imports.
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.tree import export_text
from sklearn.metrics import r2_score, accuracy_score, mean_absolute_error
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score, roc_curve


# ExplainerDashboard Imports
# from explainerdashboard import *
# from explainerdashboard.datasets import *
# from explainerdashboard.custom import *
from explainerdashboard import ClassifierExplainer, RegressionExplainer
from explainerdashboard import ExplainerDashboard

"""# **Loading Data**

Importing data using the **SimFin API** -- a robust stock analytics & data API (simfin.com)
"""
url = 'https://raw.githubusercontent.com/Ramon-Puente/stock-ml-explainer-dash/main/stock_data'
df = pd.read_csv(url,delimiter=',',on_bad_lines='skip')
df_main_clean = df.set_index(['Ticker','Date'])


# # Getting respective stock datasets
# lyts_df = df_main_clean.loc['LYTS'].copy()
# uis_df = df_main_clean.loc['UIS'].copy()

"""# **Boiler Code Functions**
---
### **Functions:**

1. **features_added** - Derives all features for our model predictors.

  Function:
  * Creates a column named *'Tomorrow'* by shifting the *'Close'* column back by 1 day
  * Creates a boolean *'Target'* column by determining if *'Tomorrow'* is greater than *'Close'*, thus representing whether the stock increases from tomorrow
  * Calculates rolling means of *'Close'* for 2 days, 3 days, and 30 days

2. **get_feature_names** - Makes a list of features for our model that are filtered by columns that are correlated with the inteded target we are predicting

3. **split_data** - Gets the training and test sets

4. **remove_spaces** - Removes spaces in the feature names, replacing them with "_"
"""

###### FEATURE ENGINEERING #######

def features_added(df):

  # Creating Prediction Target - Will the stock price increase tomorrow?
  df['Tomorrow'] = df['Close'].shift(-1)
  df['Target'] = (df['Tomorrow']>df['Close']).astype(int)


  ###### DERIVING PREDICTOR COLUMNS #######

  # Horizons are the means over the # period (1000 = the last 4 years)
  horizons = [2,3,30]

  # Deriving columns over the horizons list
  for h in horizons:

    # Calculating rolling averages
    rAvg = df.rolling(h).mean()

    # Creating a column that shows how much today's closing price delineates for the past h days average closing price
    rcol = f'How Much Todays Close $ Differs From the past {h}Days Avg Close'
    df[rcol] = df['Close'] / rAvg['Close']

    # Creating column that shows how many times the stock price increased from the last h days
    trend_column = f'How Much The Stock Price Increased From The Last {h}Days'
    df[trend_column] = df.shift(1).rolling(h).sum()['Target']

    # Dropping Nulls from the data
    df.dropna(inplace=True)

  return df

def get_feature_names(df: pd.DataFrame, bottom_limit: float, top_limit:float, target_column: str):
  """
  Get's feature names from data frame
  """
  features = []
  # Iterate through the DataFrame
  for index, row in df.iterrows():
      if bottom_limit <= row[target_column] < top_limit:
          features.append(index)

  if target_column == 'Target':
    remove = ['Open','Low', 'High', 'Close', 'Adj_Close','Tomorrow','Volume']
    features = [x for x in features if x not in remove]
  else:
    remove = ['Open','Low', 'High', 'Close', 'Adj_Close','Target','Volume']
    features = [x for x in features if x not in remove]
  return features

def split_data(df: pd.DataFrame, predictors: list, target_column: str):
  """
  Get's training and test sets
  """
  train = df[-220:].copy()
  test = df[:-220].copy()

  return train[predictors], train[target_column], test[predictors], test[target_column]

def remove_spaces(df):
    df.columns = df.columns.str.replace(' ', '_').str.replace('.','')
    return df

def feature_importance(model, df,features: list,target_column: str):
    """
    Return a DataFrame which compares the signals' Feature
    Importance in the Machine Learning model, to the absolute
    correlation of the signals and stock-returns.

    :param model: Sklearn ensemble model.
    :return: Pandas DataFrame.
    """

        # New column-name for correlation between signals and returns.
    RETURN_CORR = f'{target_column} Correlation'

    # Calculate the correlation between all data-columns.
    df_corr = df.corr()

    # Correlation between signals and returns.
    # Sorted to show the strongest absolute correlations first.
    df_corr_returns = df_corr[target_column] \
                        .abs() \
                        .drop(target_column) \
                        .sort_values(ascending=False) \
                        .rename(RETURN_CORR)

    # Wrap the list of Feature Importance in a Pandas Series.
    df_feat_imp = pd.Series(model.feature_importances_,
                            index=features,
                            name='Feature Importance')

    # Concatenate the DataFrames with Feature Importance
    # and Return Correlation.
    dfs = [df_feat_imp, df_corr_returns]
    df_compare = pd.concat(dfs, axis=1, sort=True)

    # Sort by Feature Importance.
    df_compare.sort_values(by='Feature Importance',
                           ascending=False, inplace=True)

    return df_compare.reset_index()

def plot_feature_importance(model, df,features: list,target_column: str):

  df = feature_importance(model, df,features,target_column)

  # Sort the DataFrame by either "Feature Importance" or "Return Correlation" (you can choose)
  df_sorted = df.sort_values(by="Feature Importance", ascending=False)

  # Select the top 10 features for plotting
  top_features = df_sorted.head(8)

  # Create a bar chart
  plt.figure(figsize=(10, 6))
  plt.barh(top_features["index"], top_features["Feature Importance"], color='b', label='Feature Importance')
  plt.barh(top_features["index"], top_features[f'{target_column} Correlation'], color='r', alpha=0.5, label=f'{target_column} Correlation')
  plt.xlabel('Score')
  plt.title(f'Top 8 Features: Feature Importance vs {target_column} Correlation')
  plt.legend()
  plt.tight_layout()

  plt.show()

def performance(X_test, y_test, y_pred,model, model_type='clf'):

  if model_type == 'clf':
      # Calculate accuracy
      accuracy = accuracy_score(y_test, y_pred)
      print("Accuracy:", accuracy.round(3))

      # Calculate confusion matrix
      conf_matrix2 = confusion_matrix(y_test, y_pred)

      # Calculate sensitivity (True Positive Rate)
      sensitivity = conf_matrix2[1, 1] / (conf_matrix2[1, 1] + conf_matrix2[1, 0])
      print("Sensitivity:", sensitivity.round(3))

      # Calculate specificity (True Negative Rate)
      specificity = conf_matrix2[0, 0] / (conf_matrix2[0, 0] + conf_matrix2[0, 1])
      print("Specificity:", specificity.round(3))

      # Calculate AUC-ROC
      y_prob = model.predict_proba(X_test)[:, 1]  # Probability of positive class
      roc_auc = roc_auc_score(y_test, y_prob)
      print("AUC-ROC:", roc_auc.round(3))

      # Calculate ROC curve
      fpr, tpr, thresholds = roc_curve(y_test, y_prob)

      # Plot ROC curve
      plt.figure()
      plt.plot(fpr, tpr, color='darkorange', lw=2, label='ROC curve (area = %0.2f)' % roc_auc)
      plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
      plt.xlim([0.0, 1.0])
      plt.ylim([0.0, 1.05])
      plt.xlabel('False Positive Rate')
      plt.ylabel('True Positive Rate')
      plt.title('Receiver Operating Characteristic (ROC)')
      plt.legend(loc="lower right")
      plt.show()


  else:

      # Calculate R-squared
      r2 = r2_score(y_test, y_pred)
      print("R-squared:", r2)

      # Calculate MAE
      mae = mean_absolute_error(y_test, y_pred)
      print("Mean Absolute Error:", mae)

      # Column-name for the models' predicted stock-returns.
      TOTAL_RETURN_PRED = 'Predicted'

      # Create a DataFrame with actual and predicted stock-returns.
      # This is for the training-set.
      df_y_test = pd.DataFrame(y_test)
      df_y_test[TOTAL_RETURN_PRED] = y_pred

      df_y_test.plot()

def plot_confusion_matrix(y_true, y_pred):
    """
    Plot a classification confusion matrix.

    :param y_true: Array of true classes.
    :param y_pred: Array of predicted classes.
    """

    # Class labels.
    labels = [1, 0]
    labels_text = ['Gain', 'Loss']

    # Create confusion matrix.
    mat = confusion_matrix(y_true=y_true, y_pred=y_pred, labels=labels)

    # # Normalize so all matrix entries sum to 1.0
    # mat_normalized = mat / mat.sum()

    # Create a heatmap with annotations
    plt.figure(figsize=(8, 6))
    sns.heatmap(mat, annot=True, fmt=".2f",
                xticklabels=labels_text, yticklabels=labels_text,
                cmap="Blues", cbar=True)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title("Confusion Matrix")
    plt.show()

"""# **LYTS Analysis**

## **Classification**

### **Preparing LYTS data**
"""

# Getting LYTS dataset
lyts_df = df_main_clean.loc['LYTS'].copy()

# Adding Features
lyts_df = features_added(lyts_df)

# Removing spaces from column names
lyts_df = remove_spaces(lyts_df)

# Calcualting column correlations
lyts_corr = lyts_df.corr()

# Creating features list to use as our model predictors for 'Target'
features_lyts_clf = get_feature_names(lyts_corr,
                                      0.005,
                                      0.99,
                                      'Target')

# Getting train & test sets
X_lyts_clf_train, y_lyts_clf_train, X_lyts_clf_test, y_lyts_clf_test = split_data(lyts_df,features_lyts_clf,'Target')

"""### **Creating Model**"""

model_args = \
{
    'n_estimators': 1000,
    'max_depth': 10,
    'min_samples_split': 10,
    'min_samples_leaf': 2,
    'n_jobs': -1,
    'random_state': 1234,
}

# Fitting Model
clf_lyts = RandomForestClassifier(**model_args)
clf_lyts.fit(X_lyts_clf_train,y_lyts_clf_train)

"""### **Feature Importance Analysis**"""

plot_feature_importance(clf_lyts,
                        lyts_df,
                        features_lyts_clf,
                        'Target')

"""### **Model Performance Analysis**"""

y_lyts_pred = clf_lyts.predict(X_lyts_clf_test)

performance(X_lyts_clf_test,y_lyts_clf_test,y_lyts_pred,clf_lyts)

plot_confusion_matrix(y_lyts_clf_test,y_lyts_pred)

"""## **Regression**"""

"""## **Regression**"""

# Creating features list to use as our model predictors for 'Target'
features_lyts_regr = get_feature_names(lyts_corr,
                                      0.005,
                                      0.99,
                                      'Tomorrow')

# Getting train & test sets
X_lyts_regr_train, y_lyts_regr_train, X_lyts_regr_test, y_lyts_regr_test = split_data(lyts_df,features_lyts_regr,'Tomorrow')

model_args = \
{
    'n_estimators': 1000,
    'max_depth': 10,
    'min_samples_split': 10,
    'min_samples_leaf': 2,
    'n_jobs': -1,
    'random_state': 1234,
}

# Fitting Model
regr_lyts = RandomForestRegressor(**model_args)
regr_lyts.fit(X_lyts_regr_train,y_lyts_regr_train)

plot_feature_importance(regr_lyts,
                        lyts_df,
                        features_lyts_regr,
                        'Tomorrow')

y_lyts_regr_pred = regr_lyts.predict(X_lyts_regr_test)

performance(X_lyts_regr_test,y_lyts_regr_test,y_lyts_regr_pred,regr_lyts,model_type='regr')

"""# **UIS Analysis**

## **Classification**

### **Preparing UIS data**
"""

# Getting LYTS dataset
uis_df = df_main_clean.loc['UIS'].copy()

# Adding Features
uis_df = features_added(uis_df)

# Removing spaces from column names
uis_df = remove_spaces(uis_df)

# Calcualting column correlations
uis_corr = uis_df.corr()

# Creating features list to use as our model predictors for 'Target'
features_uis_clf = get_feature_names(uis_corr,
                                      0.005,
                                      0.99,
                                      'Target')

# Getting train & test sets
X_uis_clf_train, y_uis_clf_train, X_uis_clf_test, y_uis_clf_test = split_data(uis_df,features_uis_clf,'Target')

X_uis_clf_test.columns.shape

"""### **Creating Model**"""

model_args = \
{
    'n_estimators': 1000,
    'max_depth': 10,
    'min_samples_split': 10,
    'min_samples_leaf': 2,
    'n_jobs': -1,
    'random_state': 1234,
}

# Fitting Model
clf_uis = RandomForestClassifier(**model_args)
clf_uis.fit(X_uis_clf_train,y_uis_clf_train)

"""### **Feature Importance Analysis**"""

plot_feature_importance(clf_uis,
                        uis_df,
                        features_uis_clf,
                        'Target')

"""### **Model Performance**"""

y_uis_clf_pred = clf_uis.predict(X_uis_clf_test)

performance(X_uis_clf_test,y_uis_clf_test,y_uis_clf_pred,clf_uis,model_type='clf')

"""## **Regression**"""

# Creating features list to use as our model predictors for 'Target'
features_uis_regr = get_feature_names(uis_corr,
                                      0.005,
                                      0.99,
                                      'Tomorrow')

# Getting train & test sets
X_uis_regr_train, y_uis_regr_train, X_uis_regr_test, y_uis_regr_test = split_data(uis_df,features_uis_regr,'Tomorrow')

model_args = \
{
    'n_estimators': 1000,
    'max_depth': 10,
    'min_samples_split': 10,
    'min_samples_leaf': 2,
    'n_jobs': -1,
    'random_state': 1234,
}

# Fitting Model
regr_uis = RandomForestRegressor(**model_args)
regr_uis.fit(X_uis_regr_train,y_uis_regr_train)

plot_feature_importance(regr_uis,
                        uis_df,
                        features_uis_regr,
                        'Tomorrow')

y_uis_regr_pred = regr_uis.predict(X_uis_regr_test)

performance(X_uis_regr_test,y_uis_regr_test,y_uis_regr_pred,regr_uis,model_type='regr')

"""# **Dashboards**"""
explainer = ClassifierExplainer(clf_lyts, X_lyts_clf_test, y_lyts_clf_test,labels=['Decreased Price','Increased Price'])
db = ExplainerDashboard(explainer, title="Ramon's LYTS & UIS ML Explainer Dashboard", shap_interaction=False)
db.to_yaml("dashboard.yaml", explainerfile="explainer.joblib", dump_explainer=True)

db = ExplainerDashboard.from_config("dashboard.yaml")
app = db.flask_server()
