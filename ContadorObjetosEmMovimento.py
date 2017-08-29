import datetime
import math
import cv2
import numpy as np

#variaveis globais
width = 0
height = 0
ContadorEntradas = 0
ContadorSaidas = 0
AreaContornoLimiteMin = 3000  #este valor eh empirico. Ajuste-o conforme sua necessidade 
ThresholdBinarizacao = 70  #este valor eh empirico, Ajuste-o conforme sua necessidade
OffsetLinhasRef = 150  #este valor eh empirico. Ajuste- conforme sua necessidade.

#Verifica se o corpo detectado esta entrando da sona monitorada
def TestaInterseccaoEntrada(y, CoordenadaYLinhaEntrada, CoordenadaYLinhaSaida):
        DiferencaAbsoluta = abs(y - CoordenadaYLinhaEntrada)	

        if ((DiferencaAbsoluta <= 2) and (y < CoordenadaYLinhaSaida)):
		return 1
	else:
		return 0

#Verifica se o corpo detectado esta saindo da sona monitorada
def TestaInterseccaoSaida(y, CoordenadaYLinhaEntrada, CoordenadaYLinhaSaida):
        DiferencaAbsoluta = abs(y - CoordenadaYLinhaSaida)	

	if ((DiferencaAbsoluta <= 2) and (y > CoordenadaYLinhaEntrada)):
		return 1
	else:
		return 0

camera = cv2.VideoCapture(0)

#forca a camera a ter resolucao 640x480
camera.set(3,640)
camera.set(4,480)

PrimeiroFrame = None

#faz algumas leituras de frames antes de consierar a analise
#motivo: algumas camera podem demorar mais para se "acosumar a luminosidade" quando ligam, capturando frames consecutivos com muita variacao de luminosidade. Para nao levar este efeito ao processamento de imagem, capturas sucessivas sao feitas fora do processamento da imagem, dando tempo para a camera "se acostumar" a luminosidade do ambiente

for i in range(0,20):
    (grabbed, Frame) = camera.read()

while True:
    #le primeiro frame e determina resolucao da imagem
    (grabbed, Frame) = camera.read()
    height = np.size(Frame,0)
    width = np.size(Frame,1)

    #se nao foi possivel obter frame, nada mais deve ser feito
    if not grabbed:
        break

    #converte frame para escala de cinza e aplica efeito blur (para realcar os contornos)
    FrameGray = cv2.cvtColor(Frame, cv2.COLOR_BGR2GRAY)
    FrameGray = cv2.GaussianBlur(FrameGray, (21, 21), 0)

    #como a comparacao eh feita entre duas imagens subsequentes, se o primeiro frame eh nulo (ou seja, primeira "passada" no loop), este eh inicializado
    if PrimeiroFrame is None:
        PrimeiroFrame = FrameGray
        continue

    #ontem diferenca absoluta entre frame inicial e frame atual (subtracao de background)
    #alem disso, faz a binarizacao do frame com background subtraido 
    FrameDelta = cv2.absdiff(PrimeiroFrame, FrameGray)
    FrameThresh = cv2.threshold(FrameDelta, ThresholdBinarizacao, 255, cv2.THRESH_BINARY)[1]
    
    #faz a dilatacao do frame binarizado, com finalidade de elimunar "buracos" / zonas brancas dentro de contornos detectados. 
    #Dessa forma, objetos detectados serao considerados uma "massa" de cor preta 
    #Alem disso, encontra os contornos apos dilatacao.
    FrameThresh = cv2.dilate(FrameThresh, None, iterations=2)
    _, cnts, _ = cv2.findContours(FrameThresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    QtdeContornos = 0

    #desenha linhas de referencia 
    CoordenadaYLinhaEntrada = (height / 2)-OffsetLinhasRef
    CoordenadaYLinhaSaida = (height / 2)+OffsetLinhasRef
    cv2.line(Frame, (0,CoordenadaYLinhaEntrada), (width,CoordenadaYLinhaEntrada), (255, 0, 0), 2)
    cv2.line(Frame, (0,CoordenadaYLinhaSaida), (width,CoordenadaYLinhaSaida), (0, 0, 255), 2)


    #Varre todos os contornos encontrados
    for c in cnts:
        #contornos de area muto pequena sao ignorados.
        if cv2.contourArea(c) < AreaContornoLimiteMin:
            continue

        #Para fins de depuracao, contabiliza numero de contornos encontrados
        QtdeContornos = QtdeContornos+1    

        #obtem coordenadas do contorno (na verdade, de um retangulo que consegue abrangir todo ocontorno) e
        #realca o contorno com um retangulo.
        (x, y, w, h) = cv2.boundingRect(c) #x e y: coordenadas do vertice superior esquerdo
                                           #w e h: respectivamente largura e altura do retangulo

        cv2.rectangle(Frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        #determina o ponto central do contorno e desenha um circulo para indicar
        CoordenadaXCentroContorno = (x+x+w)/2
	CoordenadaYCentroContorno = (y+y+h)/2
        PontoCentralContorno = (CoordenadaXCentroContorno,CoordenadaYCentroContorno)
        cv2.circle(Frame, PontoCentralContorno, 1, (0, 0, 0), 5)
        
        #testa interseccao dos centros dos contornos com as linhas de referencia
        #dessa forma, contabiliza-se quais contornos cruzaram quais linhas (num determinado sentido)
	if (TestaInterseccaoEntrada(CoordenadaYCentroContorno,CoordenadaYLinhaEntrada,CoordenadaYLinhaSaida)):
            ContadorEntradas += 1

	if (TestaInterseccaoSaida(CoordenadaYCentroContorno,CoordenadaYLinhaEntrada,CoordenadaYLinhaSaida)):  
            ContadorSaidas += 1

        #Se necessario, descomentar as lihas abaixo para mostrar os frames utilizados no processamento da imagem
        #cv2.imshow("Frame binarizado", FrameThresh)
        #cv2.waitKey(1);
        #cv2.imshow("Frame com subtracao de background", FrameDelta)
        #cv2.waitKey(1);


    print "Contornos encontrados: "+str(QtdeContornos)

    #Escreve na imagem o numero de pessoas que entraram ou sairam da area vigiada
    cv2.putText(Frame, "Entradas: {}".format(str(ContadorEntradas)), (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (250, 0, 1), 2)
    cv2.putText(Frame, "Saidas: {}".format(str(ContadorSaidas)), (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.imshow("Original", Frame)
    cv2.waitKey(1);


# cleanup the camera and close any open windows
camera.release()
cv2.destroyAllWindows()
