import { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Animated, Easing, Platform } from 'react-native';

import { shouldCueStopChange } from '../shift/stopCue';

const CUE_MS = 200;
const RISE = 8;
const EASE_OUT = Easing.bezier(0.23, 1, 0.32, 1);

/**
 * The style that moves the name of the next stop in (opacity and 8 px, 200 ms, run natively) each time
 * the stop changes. Pass it to an `Animated.View`.
 */
export function useStopCue(stopId: number | null) {
  const [progress] = useState(() => new Animated.Value(1));
  const [reduce, setReduce] = useState(false);
  const previous = useRef<number | null | undefined>(undefined);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduce).catch(() => undefined);
    const subscription = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduce);
    return () => subscription.remove();
  }, []);

  useEffect(() => {
    if (shouldCueStopChange(previous.current, stopId, reduce)) {
      progress.setValue(0);
      Animated.timing(progress, {
        toValue: 1,
        duration: CUE_MS,
        easing: EASE_OUT,
        useNativeDriver: Platform.OS !== 'web',
      }).start();
    }
    previous.current = stopId;
  }, [stopId, reduce, progress]);

  return {
    opacity: progress,
    transform: [{ translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [RISE, 0] }) }],
  };
}
