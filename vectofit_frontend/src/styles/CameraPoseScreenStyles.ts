import { StyleSheet, Dimensions } from 'react-native';

const { width, height } = Dimensions.get('window');

const styles = StyleSheet.create({
  parentContainer: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  childContainer: {
    flex: 1,
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
  },
  
  cameraPreview: {
    width: '100%',
    height: '100%',
    position: 'absolute',
  },
  alignmentGuideContainer: {
    ...StyleSheet.absoluteFill,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 2,
  },
  alignmentGuide45Deg: {
    width: width * 0.8,
    height: height * 0.6,
    borderWidth: 2,
    borderColor: 'rgba(249, 115, 22, 0.4)',
    borderRadius: 24,
    borderStyle: 'dashed',
  },

  topHudBar: {
    position: 'absolute',
    top: 50,
    left: 20,
    right: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    zIndex: 10,
  },
  timerBadge: {
    backgroundColor: 'rgba(30, 41, 59, 0.85)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  timerText: {
    color: '#F8FAFC',
    fontSize: 14,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
  },
  repCounterCard: {
    backgroundColor: '#1E293B',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#F97316',
    alignItems: 'center',
    minWidth: 90,
  },
  repCountNumber: {
    color: '#F97316',
    fontSize: 28,
    fontWeight: '900',
    lineHeight: 32,
  },
  repCountLabel: {
    color: '#94A3B8',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },

  feedbackOverlay: {
    position: 'absolute',
    bottom: 120,
    left: 20,
    right: 20,
    backgroundColor: 'rgba(30, 41, 59, 0.92)',
    padding: 16,
    borderRadius: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#F97316', // Defaults to orange; toggle to #EF4444 on form alert
    zIndex: 10,
  },
  feedbackTextPrimary: {
    color: '#F8FAFC',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 4,
  },
  feedbackTextSecondary: {
    color: '#94A3B8',
    fontSize: 13,
    fontWeight: '500',
  },
  alertBorder: {
    borderLeftColor: '#EF4444', // Red alert for form depth/violations
  },

  controlsBottomBar: {
    position: 'absolute',
    bottom: 40,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingHorizontal: 30,
    zIndex: 10,
  },
  recordingButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#EF4444',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 4,
    borderColor: '#F8FAFC',
  },
  recordingButtonActive: {
    backgroundColor: '#1E293B',
    borderColor: '#EF4444',
  },
  actionIconButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#1E293B',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#A855F7',
  },
});

export default styles;