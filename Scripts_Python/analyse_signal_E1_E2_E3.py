# -*- coding: utf-8 -*-
"""
Auteur : Aelaig COURNEZ - Flora GUES - Yann LAMBRECHTS - Romain SAFRAN
"""

import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as scs
import os
import glob
import pandas
from sklearn.cluster import KMeans
from mpl_toolkits.mplot3d import Axes3D

#chargement des données
def load_data(files):
    ''' Cette fonction permet de charger les donnees h5 de l'ensemble des fichiers dans une unqique base de donnees d
    '''
    d = {} # ce dictionnaire contiendra l'ensemble de la base de donnée contenue dans les differents fichiers .h5
    
    for f in files:
        line = os.path.basename(f)[:5]
        
        if line not in d:
            d[line] = {}
        # - Sauvegarde des 3 DataFrame dans le dictionnaire d - #
        d[line]['data'] = pandas.read_hdf(f,key = 'data')
        d[line]['trajectoire'] = pandas.read_hdf(f,key = 'trajectoire')
        d[line]['param'] = pandas.read_hdf(f,key = 'param') 
   
    return d
  
###########################################
#Pour info : La structure 
###########################################
k1 = ['data', 'trajectoire', 'param']
    
k2 = ['DateTime', 'Angle', 'Power', 'PowerDetectInterval', 'PowerMax',
       'Depth', 'TransmitPower', 'Mode', 'TransducerDepth', 'Heave_x',
       'Tx_Roll', 'Tx_Pitch', 'Spare1', 'Spare2', 'Rx_Roll', 'Rx_Pitch',
       'Offset', 'X', 'Y', 'Height', 'Gyro', 'Pitch', 'Roll', 'Heave_y',
       'Zone']

k3 = ['SurveyName', 'TransectName', 'SounderName', 'TransducerCount',
       'Frequency_38', 'Gain_38', 'EquivalentBeamAngle_38', 'Frequency_200',
       'Gain_200', 'EquivalentBeamAngle_200', 'Channel', 'Frequency', 'Angle',
       'SampleInterval', 'SoundVelocity', 'PulseLength', 'BandWidth',
       'AbsorptionCoefficient', 'Count', 'Mode', 'DepthMaxSave',
       'DepthMinDetect', 'DepthMaxDetect']
    
####################################
#correction vers la profondeur de référence 
def Pref(i,depth,time,nbPing,nbSmp,dref,avrPing):
  """
  i       :  la puissance enregistrée par le sondeur en W ;
  depth   :  la profondeur enegistrée de chauqes pings
  time    :  le verceteur temps des pings
  nbPing  :  le nombre de ping totale, type : int 
  nbSmp   :  le nombre d'echantillon pas ping, type : int 
  dref    :  la profondeur de reference à laquelle on veut se ramener, type : int 
  avrPing :  le nombre de ping à moyenner, type : int
  
  """
  #traitement du signal
  #Paramétres du filtre de moyenne glissantes
  b = np.arange(1,avrPing)/avrPing
  a = 1
  ####
  t_ref=[]
  debugg = False
  for p in range(0,nbPing):
    #translation temporel
    t_ref = dref*time[1]/depth[p]
    time_ref = np.arange(0,nbSmp)*t_ref
    i[:,p] = np.interp(time,time_ref,i[:,p])
    #correction de la puissance
    i[:,p] =i[:,p]*(depth[p]/dref)**3
    
    if p ==100 and debugg:
      dref = 11.5
      plt.subplot(121)
      plt.title('Étapes de transformations de la puissance pour se ramener à une profondeur de référence')
      plt.grid()
      plt.plot(time,10*np.log10(i[:,p]),'orangered',label = 'Puissance reçue au ping n° {}'.format(p))
      t_ref = dref*time[1]/depth[p]
      time_ref = np.arange(0,nbSmp)*t_ref
      i[:,p] = np.interp(time,time_ref,i[:,p])
      plt.plot(time,10*np.log10(i[:,p]),'mediumblue',label = 'Rééchantillonage temporel ' )
      i[:,p] =i[:,p]*(depth[p]/dref)**3
      plt.plot(time,10*np.log10(i[:,p]),'green',label = 'Puissance ramenée à la profondeure de référence')
      plt.xlabel('Temps en secondes')
      plt.ylabel('Puissance reçue (en dB)')
      plt.legend()
      plt.show()
      
  i_filtred = scs.lfilter(b,a,i,axis=1)
  return(i_filtred)

####################################
#Calcule de E1, E2 et E3 
def find_nearest(array, value):
    idx = (np.abs(array - value)).argmin()
    return idx

def calcule_E1_E2_E3(i_filtred,c,PulseLenght,time,nbPing,dref): 
  """
  i_filtred  :  la puissance en w corrigé de la profondeur, type : array 
  time       :  Le verceteur temps des pings, type : array 
  dref       :  La profondeur de reference à laquelle on veut se ramener, type : float 
  C          :  Celerité du son dans l'eau, type : float 
  PulsLenght :  Largeur du faisceau en seconde, type : float 
  """
  #affiche un exemple avec les aires E1 E2 et E3
  show_curve = True 
  
  E1,E2,E3 = [],[],[]
  for p in range(0,nbPing): 
    
    #temps du 1er echo
    t1 =  dref*2/c
    t1_idc = find_nearest(time, t1)
    #temps 1er echo + PulsLenght
    t2 = t1+PulseLenght
    t2_idc = find_nearest(time,t2)
    t2_stop = 2*t1*0.90
    t2_stop_idc = find_nearest(time,t2_stop)
    
    #temps du 2em echo
    t3 = t1[0]*2
    t3_idc = find_nearest(time,t3)
    t3_stop = 3*t1*0.95 
    t3_stop_idc = find_nearest(time,t3_stop)
    #tps du 3eme echo 
    t4 = t1[0]*3
    t4_idc = find_nearest(time,t4)
    t4_stop = 4*t1*0.95 
    t4_stop_idc = find_nearest(time,t4_stop)
    #E1  
    x = time
    E1_int = 0
    E2_int = 0
    E3_int = 0
    y = i_filtred[:,p]
    for j in range(t2_idc,t2_stop_idc):
        E1_int = E1_int + y[j]*(x[j+1]-x[j])
                    
    for j in range(t3_idc,t3_stop_idc):
        E2_int = E2_int + y[j]*(x[j+1]-x[j])
    
    for j in range(t4_idc,t4_stop_idc):
        E3_int = E3_int + y[j]*(x[j+1]-x[j])
        
    E1.append(E1_int)
    E2.append(E2_int)
    E3.append(E3_int)
    
    
  if show_curve :
    plt.figure()
    y = i_filtred[:,int(nbPing/2)]
    plt.plot(time,10*np.log10(y))
    y0=-120
    plt.axvline(t2,color='red',label='t début-fin E1')
    plt.axvline(t2_stop,color='red')

    plt.axvline(t3,color='green',label='t début-fin E2')
    plt.axvline(t3_stop,color='green')
    
    plt.axvline(t4,color='cyan',label='t début-fin E3')
    plt.axvline(t4_stop,color='cyan')
    

    for j in range(t2_idc,t2_stop_idc):
          E1_int = E1_int + y[j]*(x[j+1]-x[j])
          # dessin du rectangle
          x_rect = [x[j], x[j], x[j+1], x[j+1], x[j]] # abscisses des sommets
          
          y_rect = [y0   , 10*np.log10(y[j]), 10*np.log10(y[j])  , y0    , y0  ] # ordonnees des sommets
          plt.plot(x_rect,y_rect,"r")
              
    for j in range(t3_idc,t3_stop_idc):
        E2_int = E2_int + y[j]*(x[j+1]-x[j])
        # dessin du rectangle
        x_rect = [x[j], x[j], x[j+1], x[j+1], x[j]] # abscisses des sommets
        y_rect = [y0   , 10*np.log10(y[j]), 10*np.log10(y[j])  , y0     , y0   ] # ordonnees des sommets
        plt.plot(x_rect,y_rect,"g")
        
    for j in range(t4_idc,t4_stop_idc):
        E3_int = E3_int + y[j]*(x[j+1]-x[j])
        # dessin du rectangle
        x_rect = [x[j], x[j], x[j+1], x[j+1], x[j]] # abscisses des sommets
        y_rect = [y0   , 10*np.log10(y[j]), 10*np.log10(y[j])  , y0     , y0   ] # ordonnees des sommets
        plt.plot(x_rect,y_rect,"cyan")      
    plt.legend()
    plt.show()
  return(E1,E2,E3)

####################################
#Fonction d'affichage graphique issue de la docu matplotlib
def scatter_hist(x, y,c, ax, ax_histx, ax_histy):
    # no labels
    ax_histx.tick_params(axis="x", labelbottom=False)
    ax_histy.tick_params(axis="y", labelleft=False)

    # the scatter plot:
    ax.scatter(x, y,c=c)
    ax.grid()
    ax.set_xlabel('E2')
    ax.set_ylabel('E1')

    # now determine nice limits by hand:
    binwidth = 0.01
    xymax = max(np.max(np.abs(x)), np.max(np.abs(y)))
    lim = (int(xymax/binwidth) + 1) * binwidth

    bins = np.arange(-lim, lim + binwidth, binwidth)
    ax_histx.hist(x, bins=bins)
    ax_histy.hist(y, bins=bins, orientation='horizontal')


####################################
#Classification par k-mean 

#/Modifier X_c si nécéssaire pour utiliser les classificateurs désirés/
#/NE PAS OUBLIER DE CENTRER REDUIRE LES VARIABLES/!!!!

def k_mean_Classif(E1,E2,X,Y,depth,nbclass,E3=0):
  
  if len(E3)==0 :
    E3 = np.zeros(E1.shape)
    
  E1_norma = (E1-np.mean(E1))/np.std(E1)
  E2_norma = (E2-np.mean(E2))/np.std(E2)
  E3_norma = (E3-np.mean(E3))/np.std(E3)
  depth_norma = (depth-np.mean(depth))/np.std(depth)
  
  
  X_c = np.array([E1_norma,E2_norma,E3_norma]).T
  
  kmean =  KMeans(n_clusters=nbclass,algorithm='auto').fit(X_c.astype(float))
  labels = kmean.labels_
  
  if True :
    print(X_c.shape)
    plt.figure()
    plt.subplot(211)
    plt.scatter(X_c[:, 0], X_c[:, 1],c=labels.astype(float), edgecolor='k')
    plt.xlabel('E1')
    plt.ylabel('E2')
    plt.subplot(212)
    plt.scatter(X,Y,c=labels.astype(float))
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.show()
    
    labels = labels.astype(float)
    
    # definitions for the axes
    left, width = 0.1, 0.65
    bottom, height = 0.1, 0.65
    spacing = 0.005
    
    
    rect_scatter = [left, bottom, width, height]
    rect_histx = [left, bottom + height + spacing, width, 0.2]
    rect_histy = [left + width + spacing, bottom, 0.2, height]
    
    # start with a square Figure
    fig = plt.figure(figsize=(8, 8))
    
    ax = fig.add_axes(rect_scatter)
    ax_histx = fig.add_axes(rect_histx, sharex=ax)
    ax_histy = fig.add_axes(rect_histy, sharey=ax)
    
    # use the previously defined function
    scatter_hist(E2_norma, E1_norma,labels, ax, ax_histx, ax_histy)
    
  plt.show()
  return labels,X,Y

if __name__ == '__main__':

  dir_path = './fic_h5_nadir/'
  files38_h5 = glob.glob(dir_path+'*_38kHz_data.h5') # Ensemble des fichiers h5 à 38kHz à traiter (chemins)
  line = 'L0019'#,'L0008','L0018','L0019','L0024']
  d = load_data(files38_h5) # Donnees 38kHz
  
  ####################################
  #Début boucle possible ici si on veut traiter toute les lignes :
    
  Time = d[line]['data'].loc[:,'DateTime']
  Power = d[line]['data'].loc[:,'Power']
  c = d[line]['param']['SoundVelocity'].values
  PulseLenght = d[line]['param']['PulseLength'].values
  depth = d[line]['data']['Depth'].values
  X = d[line]['data']['X'].values
  Y = d[line]['data']['Y'].values
  #gérer l'exception de la ligne 24
  if line == 'L0024' :
    Power = Power[1:]
    Time = Time[1:]
    depth = depth[1:]
    X = X[1:]
    Y = Y[1:]
  
  Power = np.array([np.array(li[:]) for li in Power[:]]).T
  nbSmp = Power.shape[0]
  nbPing = Power.shape[1]
  time = np.arange(0,int(nbSmp),1)*d[line]['param']['SampleInterval'].values
  
  #conversion de dB en W
  i = 10**(Power/10)
   
  #calcule de la profondeur de référence qui sera utilisée. 
  ####################################################################################
  #ATTENTION si l'on traite toute les lignes, bien mettre une profondeur fixe !!!!!
  ####################################################################################
  dref =int(np.mean(depth)) 
  print('######################################')
  print('Ligne : {} \n'.format(line))
  print('profondeur de reference : {} m'.format(dref))
  print('######################################')
  
  i_filtred = Pref(i,depth,time,nbPing,nbSmp,dref,5)
  #calcul de E1, E2 et E3
  E1,E2,E3 = calcule_E1_E2_E3(i_filtred,c,PulseLenght,time,nbPing,dref) #i_filtred,c,PulseLenght,time,nbPing,dref,Snd_Surf
  #####################################################################
  #fin de la boucle si il y a et enregistrement des données
  
  
  ###########################
  #classification par kmean 
  ###########################
  
  #nettoyer les données 
  if False :
    E1q05 = np.quantile(E1,0.001)
    E1q95 = np.quantile(E1,0.99)
    E2q05 = np.quantile(E2,0.001)
    E2q95 = np.quantile(E2,0.99)
    cond = (E1>E1q05) & (E1 < E1q95) & (E2>E2q05) & (E2 < E2q95)
    depth = depth[cond]
    E1 = np.array(E1)[cond]
    E2 = np.array(E2)[cond]
    X = np.array(X)[cond]
    Y = np.array(Y)[cond]
    
  #Classification non supervisée, penser modifier X selon les classificateurs désirés 
  labels,Xc,Yc= k_mean_Classif(E1,E2,X,Y,depth,2,E3=E3) #E1,E2,X,Y,depth,nbclass E3 
  
  #Sauvegarde des résulats 
  # saveData(d,lines,bras_levier,patch_test,d_mnt)
  np.savetxt("./E123_2.txt",np.vstack((Xc,Yc,labels)).T,fmt='%.3f')
  

  #################################################################
  #Affichage des figures
  #################################################################
  
  if  True:
    plt.figure()
    strt = 50
    plt.title('Exemple sur un ping de la correction vers la profondeur de référence')
    plt.plot(time[strt:],i[strt:,5],label='i reçue')
    plt.plot(time[strt:],i_filtred[strt:,5],label='i normalisé à {} m et filtré sur 5 ping'.format(dref))
    plt.yscale('log')
    plt.xscale('log')
    plt.xlabel('Time')
    plt.ylabel('Puissance reçue (W)')
    plt.legend()
    plt.show()
  
  if True :
    tab = i_filtred #i
    plt.figure()
    plt.title('Image acoustique EA400 corrigée')
    mi = np.min(np.log10(tab[100:,:]))
    ma = np.max(np.log10(tab[100:,:]))
    T = time
    image = plt.imshow(10*np.log10(tab),aspect='auto', extent = (1,nbPing+1,T[-1],T[0]),vmin=-120,vmax=-20)
    plt.xlabel('ping number')
    plt.ylabel('time in seconds')
    cb = plt.colorbar()
    cb.set_label('P in dB')
  
  
  
  if True :
    plt.figure()
    plt.title('Courbes E1 et E2 pour la ligne {}'.format(line))
    plt.plot(E1,label='E1')
    plt.plot(E2,label='E2')
    plt.plot(E3,label='E3')
    plt.yscale('log')
    plt.ylabel('E1, E2, E3')
    plt.xlabel('Numéro de ping')
    plt.legend()
    
  if True : 
    E1_norma = (E1-np.mean(E1))/np.std(E1)
    E2_norma = (E2-np.mean(E2))/np.std(E2)
    plt.figure()
    
    X = d[line]['data']['X'].values
    Y = d[line]['data']['Y'].values
    
    plt.subplot(222)
    plt.title('E1 normalisé')
    plt.scatter(X,Y,c=np.log10(E1))
    plt.axis('equal')
    plt.xlabel('X')
    plt.ylabel('Y')
    
    plt.subplot(224)
    plt.title('E2 normalisé')
    plt.scatter(X,Y,c=(np.log10(E2)))
    plt.axis('equal')
    plt.xlabel('X')
    plt.ylabel('Y')
    
    plt.subplot(121)
  
    plt.title('E1 en fonction de E2 sur la ligne {}'.format(line))
    plt.plot(E2_norma,E1_norma,'+')
    plt.xlabel('E2 normalisé')
    plt.ylabel('E1 normalisé')
    plt.grid()
    plt.colorbar()
    
  if True : 
    fig = plt.figure()
    ax = Axes3D(fig)
    E1_norma = (E1-np.mean(E1))/np.std(E1)
    E2_norma = (E2-np.mean(E2))/np.std(E2)
    E3_norma= (E3-np.mean(E3)) /np.std(E3)
    ax.scatter(E2_norma, E3_norma, E1_norma,c=labels.astype(float))
    plt.xlabel('E2')
    plt.ylabel('E3')
    plt.title('E2 et E3 en fonction E1')