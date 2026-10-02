import { StyleSheet, Dimensions } from 'react-native';

const { width, height } = Dimensions.get('window');

const styles = StyleSheet.create({
  // Root Container Layout
  parentContainer: {
    flex: 1,
    backgroundColor: '#0F172A', // Slate dark backdrop
    paddingHorizontal: 16,
    paddingTop: 16,
  },

  // Header & Title Section
  headerContainer: {
    color: '#F8FAFC',
    fontSize: 24,
    fontWeight: '800',
    marginBottom: 4,
    letterSpacing: 0.2,
  },
  subHeaderText: {
    color: '#94A3B8',
    fontSize: 14,
    fontWeight: '500',
    lineHeight: 20,
  },
  instructionText: {
    color: '#CBD5E1',
    fontSize: 13,
    fontWeight: '400',
    marginBottom: 16,
  },

  // Card Shell Component
  childContainer: {
    backgroundColor: '#1E293B', // Dark slate module
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#334155',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 3,
  },

  // Camera Viewport & Detection Box
  cameraPreviewContainer: {
    width: '100%',
    height: height * 0.35,
    backgroundColor: '#020617',
    borderRadius: 16,
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#334155',
    position: 'relative',
    marginBottom: 16,
  },
  cameraOverlayFrame: {
    width: '75%',
    height: '85%',
    borderWidth: 2,
    borderColor: 'rgba(249, 115, 22, 0.5)', // Tactical orange frame guide
    borderRadius: 16,
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
  },

  // Status & Confidence Badges
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(51, 65, 85, 0.4)',
  },
  statusLabel: {
    color: '#94A3B8',
    fontSize: 13,
    fontWeight: '500',
  },
  statusBadgeActive: {
    color: '#22C55E', // Green for active detection
    fontWeight: '700',
    fontSize: 13,
  },
  statusBadgeInactive: {
    color: '#EF4444', // Red for inactive state
    fontWeight: '700',
    fontSize: 13,
  },
  confidenceValue: {
    color: '#F97316', // Tactical orange for landmark metrics
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
  },

  // Landmark Data Mesh Display
  sectionTitle: {
    color: '#F8FAFC',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 12,
  },
  landmarkGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  landmarkRow: {
    width: '48%',
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#334155',
  },
  landmarkJointTitle: {
    color: '#A855F7', // Purple accent for joint labels
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 4,
    textTransform: 'uppercase',
  },
  landmarkCoordText: {
    color: '#CBD5E1',
    fontSize: 11,
    fontWeight: '500',
    fontVariant: ['tabular-nums'],
    lineHeight: 16,
  },

  // Calibration Position Selector
  positionContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
    marginBottom: 16,
  },
  positionButton: {
    flex: 1,
    backgroundColor: '#1E293B',
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: 'center',
    marginHorizontal: 4,
    borderWidth: 1,
    borderColor: '#334155',
  },
  positionButtonActive: {
    backgroundColor: 'rgba(168, 85, 247, 0.15)',
    borderColor: '#A855F7', // Purple border active state
  },
  positionText: {
    color: '#94A3B8',
    fontSize: 13,
    fontWeight: '600',
  },
  positionTextActive: {
    color: '#A855F7',
    fontWeight: '700',
  },
});

export default styles;