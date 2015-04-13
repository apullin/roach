/* 
 * File:   ol-vibe.h
 * Author: pullin
 *
 * Created on January 20, 2014, 1:59 PM
 */

#ifndef AMS_VIBE_H
#define	AMS_VIBE_H

void amsVibeSetup();

void amsVibeStart(void);
void amsVibeStop(void);
void amsVibeSetFrequency(unsigned int channel, unsigned int incr);
void amsVibeSetAmplitude(unsigned int channel, unsigned int amp);
void amsVibeSetOffset(unsigned int channel, int off);
//void amsVibeSetAmplitudeFloat(unsigned int channel, float famp);
void amsVibeSetPhase(unsigned int channel, short phase); //short is surrogate for _Q15
int amsVibeGetOutput(unsigned int channel);
void amsVibeSetTimebase(unsigned int channel, int tb);
void amsVibeUpdate();
void amsVibeStart();
void amsVibeStop();


#endif	/* AMS_VIBE_H */
